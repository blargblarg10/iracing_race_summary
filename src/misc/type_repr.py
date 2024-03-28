def type_repr(obj, indent=0, file_path=None):
    """
    Recursively build a string representation of a nested dictionary or list
    with values replaced by their types, including proper indentation and newlines.
    Optionally, save the generated string to a specified file.
    """
    indent_str = '    ' * indent  # 4 spaces per indentation level
    if isinstance(obj, dict):
        # Handle dictionary with proper indentation and newlines
        dict_items = ',\n'.join(
            f'{indent_str}    {repr(key)}: {type_repr(value, indent + 1)}' for key, value in obj.items()
        )
        result = '{\n' + dict_items + f'\n{indent_str}}}'
    elif isinstance(obj, list):
        # Handle list with proper indentation and newlines
        list_items = ',\n'.join(
            f'{indent_str}    {type_repr(item, indent + 1)}' for item in obj
        )
        result = '[\n' + list_items + f'\n{indent_str}]'
    else:
        # Base case: Return the type name of the object
        result = obj.__class__.__name__

    # If a file path is provided, write the result to the file
    if file_path:
        with open(file_path, 'w') as file:
            file.write(result)

    return result



if __name__ == '__main__':
    nested_dict = {
        "key1": 1,
        "key2": "value",
        "key3": [1, 2, 3],
        "key4": {
            "subkey1": "str",
            "subkey2": 10.5,
            "subkey3": [True, False, {"nestedKey": None}]
        }
    }

    print(type_repr(nested_dict))