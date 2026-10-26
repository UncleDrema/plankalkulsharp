using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

namespace PlankalkulRuntime;

public sealed class MemoryFault : Exception
{
    public MemoryFault(string location, string message)
        : base($"Memory error at {location}: {message}") { }
}

// Распределитель делит одну неуправляемую область на блоки переменного размера.
// Программа хранит идентификаторы объектов, а физические адреса вычисляются
// только внутри операций чтения/записи после проверки таблицы живых объектов.
public static unsafe class Heap
{
    private const int Alignment = 8;
    private const int DefaultSize = 1024 * 1024;

    // Описывает участок области: как занятый, так и свободный.
    // Size всегда кратен Alignment и включает запас на выравнивание.
    private sealed class Block
    {
        public Block(int offset, int size, bool free) => (Offset, Size, Free) = (offset, size, free);
        public int Offset;
        public int Size;
        public bool Free;
    }

    // Описывает живой объект. Size задаётся разметкой типа в компиляторе,
    // ReservedSize — размер занятого блока. Проверки доступа используют Size,
    // поэтому, например, запас после 4-байтового числа в 8-байтовом блоке недоступен.
    private sealed class Allocation
    {
        public Allocation(int offset, int size, int reservedSize, int typeId, string typeName, string location)
            => (Offset, Size, ReservedSize, TypeId, TypeName, Location) = (offset, size, reservedSize, typeId, typeName, location);
        public readonly int Offset;
        public readonly int Size;
        public readonly int ReservedSize;
        public readonly int TypeId;
        public readonly string TypeName;
        public readonly string Location;
    }

    // Blocks покрывает всю область без промежутков и пересечений в порядке Offset.
    // После Free соседних свободных блоков не остаётся: они объединяются сразу.
    private static readonly List<Block> Blocks = [];
    // Ключ — идентификатор из значения @T, а не смещение или индекс в Blocks.
    private static readonly Dictionary<long, Allocation> Live = [];
    private static void* _memory;
    private static int _size;
    // 0 означает NIL. Счётчик не сбрасывается даже при Shutdown/Initialize:
    // новая область в том же процессе не должна оживить старые ссылки.
    private static long _nextHandle = 1;
    private static long _allocations;
    private static long _frees;
    private static int _peakUsed;
    private static bool _stats;
    private static bool _trace;
    private static Action<string>? _eventSink;

    public static void Initialize()
    {
        if (_memory != null)
            return;
        var size = ReadSize();
        _stats = ReadFlag("PLANKALKUL_MEMORY_STATS");
        _trace = ReadFlag("PLANKALKUL_MEMORY_TRACE");
        _stats |= _trace;
        InitializeCore(size);
    }

    private static void InitializeCore(int size)
    {
        // Сначала готовим метаданные, затем запрашиваем системную память.
        // Изначально вся область представлена единственным свободным блоком.
        Block firstBlock;
        try
        {
            Blocks.EnsureCapacity(1);
            firstBlock = new Block(0, size, true);
        }
        catch (Exception ex) when (ex is OutOfMemoryException or OverflowException)
        {
            throw Fault("runtime", "cannot reserve allocator metadata");
        }
        void* memory;
        try
        {
            memory = NativeMemory.AlignedAlloc((nuint)size, Alignment);
        }
        catch (OutOfMemoryException)
        {
            throw Fault("runtime", $"cannot reserve heap of {size} bytes");
        }
        if (memory == null)
            throw Fault("runtime", $"cannot reserve heap of {size} bytes");
        try
        {
            Blocks.Add(firstBlock);
        }
        catch (OutOfMemoryException)
        {
            NativeMemory.AlignedFree(memory);
            throw Fault("runtime", "cannot reserve allocator metadata");
        }
        _memory = memory;
        _size = size;
        Trace($"heap {size} bytes");
    }

    /// <summary>Initializes a run with settings supplied by the Worker.</summary>
    public static void Initialize(HeapOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        if (_memory != null)
            return;
        if (options.Size <= 0 || options.Size % Alignment != 0)
            throw Fault("runtime", "heap size must be a positive multiple of 8");
        _stats = options.Stats || options.Trace;
        _trace = options.Trace;
        _eventSink = options.EventSink;
        InitializeCore(options.Size);
    }

    public static void Shutdown()
    {
        if (_memory == null)
            return;
        try
        {
            // Отчёт снимается до очистки Live: так видны забытые освобождения.
            ReportStats();
        }
        finally
        {
            // Возвращаем системе всю область даже при ошибке вывода отчёта.
            // Это завершение работы кучи, а не сборка мусора во время программы.
            NativeMemory.AlignedFree(_memory);
            _memory = null;
            _size = 0;
            Blocks.Clear();
            Live.Clear();
            _allocations = _frees = _peakUsed = 0;
            _stats = _trace = false;
            _eventSink = null;
        }
    }

    public static void Report(MemoryFault fault) => Console.Error.WriteLine(fault.Message);

    public static HeapSnapshot Snapshot()
    {
        var free = Blocks.Where(block => block.Free).Sum(block => block.Size);
        var largest = Blocks.Where(block => block.Free).Select(block => block.Size).DefaultIfEmpty().Max();
        return new HeapSnapshot(
            new HeapStats(_allocations, _frees, UsedBytes(), free, _peakUsed, largest, Live.Count),
            Blocks.Select(block => new HeapBlock(block.Offset, block.Size, block.Free)).ToArray(),
            Live.Select(pair => new HeapObject(pair.Key.ToString(), pair.Value.TypeId, pair.Value.TypeName,
                pair.Value.Offset, pair.Value.Size, pair.Value.ReservedSize, pair.Value.Location)).ToArray());
    }

    /// <summary>Returns raw scalar values only after the executor has paused.</summary>
    public static HeapInspection Inspect(long handle, IReadOnlyList<HeapField> fields)
    {
        if (handle == 0)
            return new HeapInspection("0", [new HeapValue("", "ref", "NIL", "0")]);
        if (!Live.TryGetValue(handle, out var allocation))
            return new HeapInspection(handle.ToString(), [new HeapValue("", "stale", "freed")]);
        var values = new List<HeapValue>();
        foreach (var field in fields)
        {
            if (field.Offset < 0 || field.Size < 1 || field.Offset > allocation.Size - field.Size || field.Kind == "ref" && field.Size != 8)
            {
                values.Add(new HeapValue(field.Path, "invalid", "outside object"));
                continue;
            }
            var address = Address(allocation, field.Offset);
            var value = field.Size switch
            {
                1 => (*address).ToString(),
                4 => Unsafe.ReadUnaligned<int>(address).ToString(),
                8 => Unsafe.ReadUnaligned<long>(address).ToString(),
                _ => "unsupported",
            };
            if (field.Kind == "ref")
            {
                var target = Unsafe.ReadUnaligned<long>(address);
                // Keep the handle for navigation, but inspecting a dangling link
                // must report its state instead of dereferencing it.
                var display = target == 0 ? "NIL" : Live.ContainsKey(target) ? value : $"freed #{value}";
                values.Add(new HeapValue(field.Path, field.Kind, display, value, field.TargetTypeId));
            }
            else values.Add(new HeapValue(field.Path, field.Kind, value));
        }
        return new HeapInspection(handle.ToString(), values);
    }

    public static HeapPage InspectPage(int offset)
    {
        if (_memory == null || offset < 0 || offset >= _size) return new HeapPage(offset, _size, []);
        var bytes = new byte?[Math.Min(256, _size - offset)];
        // Free blocks may contain uninitialised system memory. Only expose bytes
        // owned by live allocations; null marks free space, not a zero byte.
        foreach (var block in Blocks)
        {
            if (block.Free) continue;
            var start = Math.Max(offset, block.Offset);
            var end = Math.Min(offset + bytes.Length, block.Offset + block.Size);
            for (var address = start; address < end; address++) bytes[address - offset] = *((byte*)_memory + address);
        }
        return new HeapPage(offset, _size, bytes);
    }

    public static long Allocate(int typeId, int size, string typeName, string location)
    {
        EnsureStarted(location);
        if (size <= 0)
            throw Fault(location, "allocation size must be positive");
        var aligned = Align(size, location);
        // First-fit: выбираем первый свободный блок достаточного размера,
        // а не самый маленький подходящий. Порядок обхода — по смещению в области.
        // ponytail: linear first-fit is intentional; add an address index only if heap profiling needs it.
        var index = -1;
        for (var i = 0; i < Blocks.Count; i++)
            if (Blocks[i].Free && Blocks[i].Size >= aligned) { index = i; break; }
        // Суммарно свободных байтов может хватать, но объекту нужен один
        // непрерывный участок. Такой отказ возможен из-за фрагментации.
        if (index < 0)
            throw Fault(location, $"out of memory allocating {aligned} bytes for {typeName}");
        if (_nextHandle == long.MaxValue)
            throw Fault(location, "reference identifier space is exhausted");

        var block = Blocks[index];
        Block? remainder = null;
        Allocation allocation;
        try
        {
            // Резервируем место в коллекциях и создаём новые описатели до
            // изменения блока: ошибка подготовки оставит его свободным.
            Blocks.EnsureCapacity(checked(Blocks.Count + 1));
            Live.EnsureCapacity(checked(Live.Count + 1));
            if (block.Size != aligned)
                remainder = new Block(block.Offset + aligned, block.Size - aligned, true);
            allocation = new Allocation(block.Offset, size, aligned, typeId, typeName, location);
        }
        catch (Exception ex) when (ex is OutOfMemoryException or OverflowException)
        {
            throw Fault(location, "cannot reserve allocator metadata");
        }

        // Идентификатор новый даже при повторном использовании прежнего Offset.
        // Очищаем и полезные байты, и выравнивание: все поля-ссылки станут NIL.
        var handle = _nextHandle++;
        Unsafe.InitBlockUnaligned((byte*)_memory + block.Offset, 0, (uint)aligned);
        if (block.Size == aligned)
            block.Free = false;
        else
        {
            // Занимаем начало найденного блока, хвост остаётся свободным.
            // Вставка сразу после него сохраняет порядок Blocks по Offset.
            Blocks.Insert(index + 1, remainder!);
            block.Size = aligned;
            block.Free = false;
            Trace($"split {block.Offset}: {aligned} + {Blocks[index + 1].Size}");
        }
        // Публикуем связь «идентификатор -> объект» для последующих обращений.
        Live.Add(handle, allocation);
        _allocations++;
        _peakUsed = Math.Max(_peakUsed, UsedBytes());
        Trace($"allocate #{handle} {typeName} {aligned} bytes at {block.Offset}");
        return handle;
    }

    public static void Free(long handle, int expectedTypeId, string location)
    {
        if (handle == 0)
            return;
        var allocation = Get(handle, expectedTypeId, 0, 0, location);
        // Get проверяет живость и тип до изменения метаданных. Ищем блок по
        // сохранённому смещению; само числовое значение handle адресом не является.
        var index = Blocks.FindIndex(block => block.Offset == allocation.Offset && !block.Free);
        if (index < 0)
            throw Fault(location, "allocator metadata is inconsistent");

        // Все копии ссылки теряют действительность через удаление одной записи.
        // Объекты, на которые указывали поля освобождаемого объекта, не затрагиваем.
        Live.Remove(handle);
        Blocks[index].Free = true;
        _frees++;
        Trace($"free #{handle} {allocation.TypeName} {allocation.ReservedSize} bytes at {allocation.Offset}");
        if (index > 0 && Blocks[index - 1].Free)
        {
            // Присоединяем освобождённый блок к левому; текущим становится левый.
            Blocks[index - 1].Size += Blocks[index].Size;
            Blocks.RemoveAt(index);
            index--;
            Trace($"merge at {Blocks[index].Offset}: {Blocks[index].Size}");
        }
        if (index + 1 < Blocks.Count && Blocks[index + 1].Free)
        {
            // Проверяем правого соседа уже после возможного слияния слева.
            // Двух проверок достаточно: до Free соседние свободные блоки слиты.
            Blocks[index].Size += Blocks[index + 1].Size;
            Blocks.RemoveAt(index + 1);
            Trace($"merge at {Blocks[index].Offset}: {Blocks[index].Size}");
        }
    }

    // Каждый доступ заново разрешает handle через Get. Наружу возвращается
    // только значение; сырой адрес не переживает вызов пользовательской функции.
    public static int ReadByte(long handle, int typeId, int offset, string location)
        => *Address(Get(handle, typeId, offset, 1, location), offset);

    public static void WriteByte(long handle, int typeId, int offset, int value, string location)
    {
        if ((uint)value > byte.MaxValue)
            throw Fault(location, "byte value is outside 0..255");
        *Address(Get(handle, typeId, offset, 1, location), offset) = (byte)value;
    }

    public static int ReadInt32(long handle, int typeId, int offset, string location)
        => Unsafe.ReadUnaligned<int>(Address(Get(handle, typeId, offset, sizeof(int), location), offset));

    public static void WriteInt32(long handle, int typeId, int offset, int value, string location)
        => Unsafe.WriteUnaligned(Address(Get(handle, typeId, offset, sizeof(int), location), offset), value);

    public static long ReadInt64(long handle, int typeId, int offset, string location)
        => Unsafe.ReadUnaligned<long>(Address(Get(handle, typeId, offset, sizeof(long), location), offset));

    public static void WriteInt64(long handle, int typeId, int offset, long value, string location)
        => Unsafe.WriteUnaligned(Address(Get(handle, typeId, offset, sizeof(long), location), offset), value);

    private static Allocation Get(long handle, int expectedTypeId, int offset, int width, string location)
    {
        EnsureStarted(location);
        if (handle == 0)
            throw Fault(location, "cannot dereference NIL");
        if (!Live.TryGetValue(handle, out var allocation))
            throw Fault(location, $"reference #{handle} is not live");
        if (allocation.TypeId != expectedTypeId)
            throw Fault(location, $"reference #{handle} has type {allocation.TypeName}, not expected type");
        // Проверяем диапазон относительно размера объекта, не ReservedSize.
        // Вычитание вместо offset + width не даёт переполнению обойти проверку.
        if (offset < 0 || width < 0 || offset > allocation.Size - width)
            throw Fault(location, "object access is outside its bounds");
        return allocation;
    }

    // Вызывается только с описателем и смещением, уже проверенными Get.
    private static byte* Address(Allocation allocation, int offset) => (byte*)_memory + allocation.Offset + offset;

    private static int Align(int size, string location)
    {
        // Для Alignment = 8 прибавляем 7 и обнуляем три младших бита.
        // checked отклоняет слишком большой запрос вместо перехода к отрицательному размеру.
        try { return checked((size + Alignment - 1) & -Alignment); }
        catch (OverflowException) { throw Fault(location, "allocation size is too large"); }
    }

    private static void EnsureStarted(string location)
    {
        if (_memory == null)
            throw Fault(location, "heap is not initialized");
    }

    private static int ReadSize()
    {
        var text = Environment.GetEnvironmentVariable("PLANKALKUL_HEAP_SIZE");
        if (string.IsNullOrEmpty(text))
            return DefaultSize;
        if (!long.TryParse(text, out var value) || value <= 0 || value > int.MaxValue || value % Alignment != 0)
            throw Fault("runtime", "PLANKALKUL_HEAP_SIZE must be a positive multiple of 8 not exceeding Int32.MaxValue");
        return (int)value;
    }

    private static bool ReadFlag(string name)
    {
        var value = Environment.GetEnvironmentVariable(name);
        if (string.IsNullOrEmpty(value) || value == "0")
            return false;
        if (value == "1")
            return true;
        throw Fault("runtime", $"{name} must be 0 or 1");
    }

    private static MemoryFault Fault(string location, string message) => new(location, message);

    // Статистика учитывает реально занятые блоки вместе с выравниванием.
    private static int UsedBytes() => Live.Values.Sum(allocation => allocation.ReservedSize);

    private static void Trace(string message)
    {
        _eventSink?.Invoke(message);
        if (_trace)
            Console.Error.WriteLine($"memory: {message}");
    }

    private static void ReportStats()
    {
        if (!_stats)
            return;
        var free = Blocks.Where(block => block.Free).Sum(block => block.Size);
        var largest = Blocks.Where(block => block.Free).Select(block => block.Size).DefaultIfEmpty().Max();
        Console.Error.WriteLine($"memory: allocations={_allocations} frees={_frees} used={UsedBytes()} free={free} peak={_peakUsed} largest-free={largest} live={Live.Count}");
        foreach (var pair in Live)
            Console.Error.WriteLine($"memory: live #{pair.Key} {pair.Value.TypeName} allocated at {pair.Value.Location}");
    }
}
