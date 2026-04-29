# PlankalkulSharp

Компилятор языка Plankalkül (первый в истории язык программирования, Конрад Цузе, 1945) для платформы .NET CLR.

Курсовая работа по курсу «Разработка компиляторов».

## Синтаксис

Линейная текстовая нотация для записи программ на Plankalkül:

- **`=>`** — оператор присваивания (Ergibt-Zeichen): `V0 + V1 => R0`
- **`->`** — условный оператор (Bedingung): `(V0 < V1) -> V1 => Z0`
- **`->`** в сигнатуре программы: `P1 max (V0[:8.0], V1[:8.0]) -> R0[:8.0]`

Пример программы:

```
P1 max (V0[:8.0], V1[:8.0]) -> R0[:8.0]
  V0[:8.0] => Z1[:8.0]
  (Z1[:8.0] < V1[:8.0]) -> V1[:8.0] => Z1[:8.0]
  Z1[:8.0] => R0[:8.0]
END
```

## Архитектура

```
Исходный код (.pk)
    │
    ▼
┌──────────────────┐
│  Лексер / Парсер │  ANTLR4 — grammar/Plankalkul.g4
│  (frontend)      │  CST → AST (ast_builder.py)
└────────┬─────────┘
         │  AST (ast/nodes.py)
         ▼
┌──────────────────┐
│  Семантический   │  Таблица символов, разрешение типов,
│  анализ          │  проверка типов (semantic/analyzer.py)
└────────┬─────────┘
         │  Проверенный AST + ResolvedType
         ▼
┌──────────────────┐
│  Генерация кода  │  CIL текстовый ассемблер
│  (codegen)       │  (codegen/emitter.py)
└────────┬─────────┘
         │  .il файл
         ▼
┌──────────────────┐
│  ilasm           │  Microsoft.NET.Sdk.IL / dotnet build
│  (сборка)        │
└────────┬─────────┘
         │
         ▼
    .NET сборка (.dll)
```

## Стек технологий

| Компонент         | Технология                          |
| ----------------- | ----------------------------------- |
| Язык реализации   | Python 3.14+                        |
| Менеджер пакетов  | uv                                  |
| Генератор парсера | ANTLR4 4.13.2                       |
| Целевая платформа | .NET CLR (CIL)                      |
| Сборка IL         | Microsoft.NET.Sdk.IL (dotnet build) |
| Тестирование      | pytest                              |

## Структура проекта

```
plankalkulsharp/
├── grammar/
│   └── Plankalkul.g4              # ANTLR4 грамматика
├── docs/
│   ├── bnf-grammar.md             # Формальная грамматика (BNF)
│   ├── language-reference.md      # Спецификация языка
│   └── notation.md                # Линейная текстовая нотация
├── src/plankalkulsharp/
│   ├── ast/nodes.py               # Узлы AST (frozen dataclasses)
│   ├── frontend/
│   │   ├── ast_builder.py         # CST → AST (ANTLR4 visitor)
│   │   └── generated/             # Сгенерированный лексер/парсер
│   ├── semantic/
│   │   └── analyzer.py            # Таблица символов, проверка типов
│   ├── codegen/
│   │   └── emitter.py             # Генератор CIL (.il)
│   ├── compiler.py                # Пайплайн: parse → check → emit
│   └── __main__.py                # CLI
├── build/
│   └── PlankalkulProgram.ilproj   # .NET проект для сборки IL
├── tests/
│   ├── programs/                  # Тестовые программы на Plankalkül
│   ├── test_parser.py             # Тесты парсера (20)
│   ├── test_semantic_codegen.py   # Тесты семантики и базовой генерации (17)
│   ├── test_il_output.py          # Тесты сгенерированного IL (63)
├── scripts/
│   └── generate_parser.py         # Генерация парсера из .g4
└── pyproject.toml
```

## Быстрый старт

### Установка зависимостей

```bash
uv sync
```

### Генерация парсера (если нужно пересоздать)

```bash
uv run python scripts/generate_parser.py
```

### Запуск тестов

```bash
uv run pytest tests/ -v
```

100 тестов покрывают все фазы компилятора: парсер, семантический анализ, генерацию IL.

### Компиляция и запуск программы

Полный пайплайн от исходного кода до исполняемого файла:

```bash
# 1. Plankalkül → CIL ассемблер (.il)
uv run python -m plankalkulsharp compile tests/programs/max.pk -o build/PlankalkulProgram.il --emit-il

# 2. CIL → .NET сборка (.dll)
cd build
dotnet build

# 3. Запуск с аргументами
dotnet run -- 3 7
```

### Примеры запуска

| Программа        | Описание              | Команда             | Результат |
| ---------------- | --------------------- | ------------------- | --------- |
| `max.pk`         | Максимум двух чисел   | `dotnet run -- 3 7` | **7**     |
| `arithmetic.pk`  | (a+b)×2−1             | `dotnet run -- 3 4` | **13**    |
| `forloop.pk`     | Сумма 0..n (FOR-цикл) | `dotnet run -- 5`   | **15**    |
| `guard_block.pk` | Модуль числа (guard)  | `dotnet run -- -42` | **42**    |
| `loop.pk`        | Счёт до 10 (W-цикл)   | `dotnet run`        | **10**    |

### CLI

```bash
# Вывести AST файла
uv run python -m plankalkulsharp parse tests/programs/max.pk

# Скомпилировать в .il (без сборки)
uv run python -m plankalkulsharp compile tests/programs/max.pk --emit-il

# Скомпилировать с указанием выходного файла
uv run python -m plankalkulsharp compile tests/programs/max.pk -o output.il --emit-il
```

## Документация

- [Формальная грамматика (BNF)](docs/bnf-grammar.md) — формальное описание синтаксиса языка
- [Спецификация языка](docs/language-reference.md) — типы данных, переменные, операции, семантические правила
- [Линейная нотация](docs/notation.md) — текстовый формат записи программ
- [ANTLR4 грамматика](grammar/Plankalkul.g4) — реализация грамматики для генератора парсера
