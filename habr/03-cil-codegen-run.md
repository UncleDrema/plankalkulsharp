# Plankalkül -> CIL -> .NET: генерация и запуск. Часть 3

В первых двух частях мы дошли до точки, где программа на Plankalkül уже разобрана, превращена в AST и проверена семантическим анализатором. Осталось главное: получить исполняемый результат.

В PlankalkulSharp backend генерирует CIL - Common Intermediate Language для .NET. Это текстовый IL-ассемблер, который затем собирается через `dotnet build` с помощью проекта на `Microsoft.NET.Sdk.IL`.

## Почему CIL

Для учебного компилятора есть несколько типичных вариантов backend-а:

- интерпретировать AST напрямую;
- генерировать C, C#, JavaScript или другой высокоуровневый язык;
- генерировать байткод собственной VM;
- генерировать IR или assembly существующей платформы.

В этом проекте выбран CIL, потому что он дает интересный баланс. С одной стороны, это достаточно низкий уровень: нужно думать о стеке, locals, labels и инструкциях перехода. С другой стороны, не нужно писать собственный runtime, загрузчик модулей и сборщик исполняемых файлов. CLR уже умеет выполнять результат.

Pipeline backend-а выглядит так:

```text
checked AST
  |
  v
CILEmitter
  |
  v
PlankalkulProgram.il
  |
  v
dotnet build
  |
  v
PlankalkulProgram.exe / PlankalkulProgram.dll
```

## Как сущности Plankalkül ложатся на CLR

Самое приятное в этом backend-е - почти прямое отображение некоторых идей языка на CIL.

| Plankalkül | CIL/.NET |
| --- | --- |
| программа `P0 max` | static method `max` |
| `V0`, `V1` | аргументы метода |
| `Z0`, `Z1` | local variables |
| `R0` | local result + return value |
| `C0`, `C1` | locals для констант |
| `->` guard | comparison + branch |
| `W` и `FOR` | labels + `br`/`brtrue`/`brfalse` |
| массив | CLR array |
| record | CIL value type |

Для примера снова возьмем `max.pk`:

```text
int = 8.0

P0 max (V0[:int], V1[:int]) -> R0[:int]
  V0 => Z1
  (Z1 < V1) -> V1 => Z1
  Z1 => R0
END
```

Естественное CIL-представление метода выглядит примерно так:

```assembly
.method public hidebysig static int32 max(int32 V_0, int32 V_1) cil managed
{
  .maxstack 8
  .locals init (
    int32 R_0,
    int32 Z_1
  )

  ldarg V_0
  stloc Z_1

  ldloc Z_1
  ldarg V_1
  clt
  brfalse GEND_0

  ldarg V_1
  stloc Z_1

GEND_0:
  ldloc Z_1
  stloc R_0
  ldloc R_0
  ret
}
```

Это не обязательно байт-в-байт полный generated файл, но показывает ключевую механику. Значение `V0` загружается из аргументов и кладется в local `Z1`. Сравнение `Z1 < V1` дает boolean на стеке. `brfalse` перескакивает через тело guard-а, если условие ложно.

## Присваивание

Оператор Plankalkül:

```text
V0 => Z1
```

для простого integer-like значения превращается в пару инструкций:

```assembly
ldarg V_0
stloc Z_1
```

Если источник - local, будет `ldloc`. Если цель - local, будет `stloc`. Если цель - поле record-а или элемент массива, генератор должен выдать уже другую последовательность: загрузить адрес/массив, индекс, значение и вызвать `stfld` или `stelem`.

Именно поэтому semantic analysis из предыдущей части так важен. Backend должен знать, что справа от `=>`: простая переменная, элемент массива, поле записи или вложенный component access.

## Guards и ветвления

Guard:

```text
(Z1 < V1) -> V1 => Z1
```

имеет простую структуру:

```text
evaluate condition
if false: jump to end
emit guarded body
end:
```

В CIL это превращается в labels и conditional branch:

```assembly
ldloc Z_1
ldarg V_1
clt
brfalse GEND_0

ldarg V_1
stloc Z_1

GEND_0:
```

Для вложенных guard-ов генератор просто создает несколько таких участков с разными labels.

## Циклы W и FOR

`W`-loop в Plankalkül удобнее всего генерировать как цикл с флагом: если за проход сработал хотя бы один guard, нужно повторить тело.

Упрощенная схема:

```text
WTOP:
  fired = false
  check guard 1
  if true:
    fired = true
    body 1
  check guard 2
  if true:
    fired = true
    body 2
  if fired: goto WTOP
WEND:
```

`FOR` генерируется ближе к привычному счетному циклу: инициализация переменной, label начала, проверка верхней границы, тело, increment, переход назад.

В тестах IL это проверяется не запуском на глаз, а конкретными признаками: наличие labels, `brtrue`, `bgt`, `ldc.i4.1`, `add` и перехода к началу цикла.

## Records и arrays

Составные типы - самая интересная часть backend-а.

Массив Plankalkül:

```text
A2 = 100 x A1
```

становится CLR-массивом. Если `A1` - record, то это массив value type-ов.

Record:

```text
A1 = (S1.8, S1.8)
```

можно представить как generated value type с полями:

```assembly
.class public sequential ansi sealed beforefieldinit Rec_0
       extends [System.Runtime]System.ValueType
{
  .field public int32 f_0
  .field public int32 f_1
}
```

После этого обращение к компонентам вроде:

```text
Z0[Z1.1 : A2]
```

может генерировать доступ к элементу массива и полю записи. В IL-тестах для таких программ проверяется наличие `newarr`, `ldelema`, `ldfld` и `stfld`.

## Сложный пример: reverse_list

Программа `reverse_list.pk` демонстрирует, что проект умеет больше, чем арифметику и `max`.

В ней узел списка описан как record:

```text
A1 = (S1.8, S1.8)
A2 = 100 x A1
```

Список хранится в массиве `Z0`. Вместо указателей используются индексы:

```text
FOR Z1[:8.0] FROM 0 TO Z2[:8.0] {
  Z1[:8.0] => Z0[Z1.0 : A2]
  Z1[:8.0] + 1 => Z0[Z1.1 : A2]
}
```

Разворот списка выглядит как классический алгоритм с `prev`, `curr` и `next`, только все значения лежат в `Z`-переменных:

```text
W {
  (Z5[:8.0] != Z3[:8.0]) -> {
    Z0[Z5.1 : A2] => Z6[:8.0]
    Z4[:8.0] => Z0[Z5.1 : A2]
    Z5[:8.0] => Z4[:8.0]
    Z6[:8.0] => Z5[:8.0]
  }
}
```

Для backend-а это хороший стресс-тест: здесь одновременно нужны arrays, records, dynamic component access, `FOR`, `W`, comparisons и assignments в поля.

## CLI: parse, analyze, compile

У проекта есть CLI с тремя основными командами.

Посмотреть AST:

```bash
uv run python -m plankalkulsharp parse tests/programs/max.pk
```

Запустить семантический анализ:

```bash
uv run python -m plankalkulsharp analyze tests/programs/max.pk
```

Сгенерировать IL:

```bash
uv run python -m plankalkulsharp compile tests/programs/max.pk -o build/PlankalkulProgram.il --emit-il
```

Если не останавливаться на `--emit-il`, CLI использует helper project в `build/` и запускает сборку через .NET.

Ручной путь выглядит так:

```bash
uv run python -m plankalkulsharp compile tests/programs/max.pk -o build/PlankalkulProgram.il --emit-il
cd build
dotnet build
dotnet run -- 3 7
```

Ожидаемый результат для `max(3, 7)`:

```text
7
```

## Как это тестируется

Компилятор сложно тестировать одним уровнем проверок. В проекте используется несколько слоев.

Parser tests проверяют, что синтаксис разбирается и превращается в ожидаемые конструкции.

Semantic tests проверяют смысловые правила: типы, переменные, вызовы, корректность операций.

IL shape tests не запускают программу, а проверяют generated IL как текст: method signatures, locals, labels, инструкции `add`, `clt`, `brfalse`, `newarr`, `ldfld`, `stfld`.

E2E tests идут дальше: компилируют `.pk` в `.il`, собирают через `dotnet build`, запускают результат и сравнивают stdout.

Пример набора e2e-сценариев:

| Программа | Аргументы | Ожидаемый результат |
| --- | --- | --- |
| `max.pk` | `3 7` | `7` |
| `arithmetic.pk` | `3 4` | `13` |
| `forloop.pk` | `5` | `15` |
| `fibonacci.pk` | `10` | `55` |
| `reverse_list.pk` | `5 1` | `3` |

Такой тестовый контур особенно полезен для backend-а. Можно не только увидеть, что программа "как-то работает", но и проверить, что конкретная языковая конструкция компилируется в ожидаемые CIL-паттерны.

## Ограничения и планы

Проект все еще учебный, и это нормально. В нем есть места, которые хочется развивать дальше:

- улучшить диагностику ошибок;
- аккуратнее оформить поддержку records и component access;
- расширить набор примеров ближе к историческим программам Plankalkül;
- добавить больше негативных semantic tests;
- стабилизировать документацию вокруг поддерживаемого подмножества языка;
- подумать об оптимизациях generated IL.

Но даже в текущем виде путь уже полный: от `.pk`-файла до программы, которую можно собрать и запустить в .NET.

## Что дальше

На этом базовая серия закончена: история и нотация, frontend и semantic analysis, backend и запуск. Дальше из нее можно сделать отдельные более узкие статьи: про тестирование компиляторов, про генерацию CIL руками, про records/arrays или про попытку приблизиться к оригинальной двумерной нотации Plankalkül.

TODO перед публикацией:

- вставить реальный IL-фрагмент, сгенерированный текущей версией `CILEmitter`;
- проверить команды на чистом окружении;
- решить, использовать ли `reverse_list.pk` как финальный пример или заменить его на более короткий `fibonacci.pk`;
- прогнать статью через предпросмотр Habr Markdown.
