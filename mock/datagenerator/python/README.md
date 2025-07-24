# Data Generator

The **Data Generator** library helps developers quickly create mock data based on a simple, user-defined schema.

It's useful for:
- Testing APIs
- Prototyping UIs
- Seeding databases
- Any case where mock data is needed

It follows principles from the [JSON Schema](https://json-schema.org/learn/getting-started-step-by-step) and aims to be lightweight, flexible, and easy to use.

This is the **first version**, focused on **basic functionality**, **simplicity**, and **clear design**.

Useful links:
- [Faker](https://faker.readthedocs.io/en/master/#basic-usage)
- [Mockjs](https://github.com/nuysoft/Mock/wiki)
- [rstr - a helper module for easily generating random strings of various types](https://pypi.org/project/rstr/)
- [JSON Schema Tools](https://json-schema.org/tools?query=&sortBy=name&sortOrder=ascending&groupBy=toolingTypes&licenses=&languages=&drafts=&toolingTypes=&environments=&showObsolete=false&supportsBowtie=false)
  - JSON Schema Generator
    - [jsonschema-generator](https://github.com/victools/jsonschema-generator)
    - [Pydantic - Generates schemas from Python models based on Python 3.6+ type hints.](https://github.com/pydantic/pydantic)
    - [json-schema-inferrer - Data to Schema]****(https://github.com/saasquatch/json-schema-inferrer)
  - JSON Schema Validator
    - [jsonschema](https://github.com/python-jsonschema/jsonschema)
- [JSON Schema Data Types](https://json-schema.org/understanding-json-schema/reference/type)

## 🚀 Getting Started

```bash
# Set up a virtual environment (optional but recommended)
python3 -m venv .venv
sh .venv/Scripts/activate & source .venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt
pip install mypy

# Exit environment
deactivate
```

## How It Works

You define a schema, which describes what properties each data row should include and how to generate their values. Optionally, you can choose the output format (e.g., JSON, CSV), or define a template string for custom formatting.

### Schema Format

The schema supports both detailed object-based definitions and shortcut expressions. Each property can be randomly generated or assigned a fixed value.

```json
{
  "properties": {
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 10
    },
    "age": {
      "type": "number",
      "min": 1,
      "max": 100
    },
    "gender": {
      "type": "enum",
      "value": ["female", "male"]
    },
    "height": {
      "type": "number",
      "value": 170
    },
    "firstName": {
      "type": "string",
      "value": "Zhang"
    }
  },
  "format": "json",
  "template": "My name is {{name}}, age: {{age}}, gender: {{gender}}"
}
```

#### Schema Fields

- **properties** _(required)_ 

Defines the properties and the rules for generating values.

Supported Types:

| Type      | Object Format Example                                   | Shortcut        | Description                                       |
| --------- | ------------------------------------------------------- | --------------- | ------------------------------------------------- |
| `string`  | `{ "type": "string", "minLength": 1, "maxLength": 10 }` | `str(1, 10)`    | Random string between `minLength` and `maxLength` |
| `number`  | `{ "type": "number", "minimum": 1, "maximum": 100 }`    | `num(1, 100)`   | Random number between `minimum` and `maximum`     |
| `enum`    | `{ "type": "enum", "value": ["a", "b", "c"] }`          | `enum(a, b, c)` | Random value from the list                        |
| `boolean` | `{ "type": "boolean", "value": true }`                  | `bool()`        | Randomly returns true or false                    |
| Fixed     | `{ "type": "number", "value": 42 }` or just `42`        | `42`            | Always returns the fixed number or string value   |


Example (Shortcut Format)

```json
"properties": {
  "name": "str(1, 10)",
  "age": "num(1, 100)",
  "gender": "enum(female, male)",
  "height": 170,
  "firstName": "Zhang",
  "active": "bool()"
}
```

> If a value is not a generator expression (`str(...)`, `int(...)`, `enum(...)`), it is treated as a fixed constant.

- **format** _(optional, default: "json")_

Specifies the output format of each row. Supported values include:

- `"json"`: Outputs each row as a JSON object.
- `"csv"`: Outputs comma-separated values (same as `"sep(,)"`).
- `"sep(<separator>)"`: Outputs values separated by a custom delimiter (e.g., `sep(|)`, `sep(\\t)`).

> ⚠️ If template is defined, the format setting is ignored.

- **template** _(optional)_

Defines a custom output format using placeholders. You can reference any property defined in `properties` using `{{property}}`.

Example:

```json
"template": "My name is {{name}}, age: {{age}}, gender: {{gender}}"
```

>⚠️ If `template` is defined, the `format` setting will be ignored.


## 📅 Planned Features (Future Versions)

These are not yet implemented, but may be added later:

- [ ] Optional properties

Allow a property to be optionally included.

```json
"nickname": "optional(str(1, 5))"
```

- [ ] Nullable properties

Allow a property to randomly be null.

```json
"score": "nullable(int(0, 100))"
```

- [ ] Nested objects

Enable support for structured and nested data.

```json
"address": {
  "type": "object",
  "properties": {
    "city": "str(3, 20)",
    "zip": "int(10000, 99999)"
  }
}
```

- [ ] Arrays (e.g. "tags": "array(enum(a, b, c), 1, 5)")

Support arrays with randomly generated elements.

```json
"tags": {
    "type": "array",
    "items": {
        "anyOf": [
          { "type": "number" },
          { "type": "enum", "value": ["a", "b", "c"] }
        ]
    },
    "minItems": 1,
    "uniqueItems": true
}

// shortcut
"tags": "array(enum(a, b, c), 1, 5)"
```

- [ ] Value dependencies between properties

Allow one property's value to be dependent on another.
Example: If `country = CN`, then `language = Chinese`.

You can express this using inline SQL-like syntax:

```sql
"language": "select case when $.country='CN' then 'Chinese' else 'English' from $ where $.country = 'CN'"
```

> 💡 $ refers to the current record being generated.

- [ ] Regex-based string generation

Generate strings using regular expression patterns.

```
"code": "regex([A-Z]{3}-[0-9]{4})"
```

- [ ] Support for Faker integration

Use the [Faker](https://faker.readthedocs.io/) library to generate realistic values like emails, phone numbers, etc.

```json
"phone": { "type": "faker", "value": "phone_number" },
"email": { "type": "faker", "value": "email" }
```

- [ ] Support for JSON Schema input

Support importing existing JSON Schema definitions.

```json
{
  "$ref": "https://example.com/geographical-location.schema.json",
  "type": "object",
  // extra properties
  "properties": {
    "id": { "type": "integer", "minimum": 1, "maximum": 1000 },
    "name": { "type": "string", "minLength": 1, "maxLength": 10 }
  }
}
```