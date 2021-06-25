# How To: Import JSON Organized Data Into MIQA

# Introduction
The latest version of MIQA saw some small tweaks to the schema for imports. Future imports into MIQA will need to be updated to utilize this modified schema. Future exports will return data in this modified schema and any other systems ingesting the data will need modification to successfully read the schema.

# Changes in Schema

## Meta Information
Some meta information has been moved from the tail of the document to the head. This in and of itself should not affect the JSON import files.

Some additional changes to the meta information commented in below code may require changes:


### New Schema:
```js
schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'MIQA data import schema',
    'type': 'object',
    'additionalProperties': False,
    'required': ['data_root', 'sites', 'experiments', 'scans'], // The required properties have been expanded from 'scans' to include 'data_root', 'sites', 'experiments'
    'properties': { // Instead of referring to the `properties` object, the properties are passed inline
        ...
    },
}
```

### Previous Schema:
```js
schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'MIQA data import schema',
    'type': 'object',
    'additionalProperties': False,
    'required': ['scans'],
    'properties': properties,
}
```

## Sites: id => name
```js
...
'sites': {
    'type': 'array',
    'items': {
        ...
        'required': ['name'], // Previously ['id']
        'properties': {
            'name': {'type': 'string'}, // Previously 'id': {'type': 'string'},
        },
    },
},
...
```

## Scans: add_properties => additionalProperties, imagePattern => image_pattern
```js
...
'scans': {
    'type': 'array',
    'items': {
        ...
        'user_fields': {
            ...
            'additionalProperties': True, // previously 'additional_properties': True,
        },
        ...
        'image_pattern': {'type': 'string'}, // previously 'imagePattern': {'type': 'string'},
    },
    'oneOf': [
        ...
        {
            'required': [
                ...
                'image_pattern',
            ],
        },
    ],
},
...
```
