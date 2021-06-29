# How To: Import JSON Organized Data Into MIQA

# Introduction
The latest version of MIQA saw some small tweaks to the schema for datasets. This means:
- Future imports into MIQA will need to be updated to utilize this modified schema. 
- Future exports will return data in this modified schema.
- Any other systems ingesting export datasets will need to be modified to match the updated schema successfully.

# Changes in Schema

## Meta Information
Some meta information has been moved from the tail of the document to the head. This in and of itself should not affect the JSON import files.

Some additional changes to the meta information may require changes (see comments inline below):


### New Schema:
```js
schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'MIQA data import schema',
    'type': 'object',
    'additionalProperties': False,
    'required': ['data_root', 'sites', 'experiments', 'scans'], // The required properties have been expanded from 'scans' to 'scans', 'data_root', 'sites', 'experiments'
    'properties': { // Instead of referring to the `properties` object, the properties are passed inline, previously we had 'properties': properties,
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
    'properties': properties, // Here properties referred to a separate properties object defined in the same schema
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
                'image_pattern', // previous 'imagePattern': {'type': 'string},
            ],
        },
    ],
},
...
```
