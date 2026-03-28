"""
🔍 Event System Validator
Validates: event_types_list.json, handlers_list.json, event_handler_mapping.json against event_types_structure.json
"""
import os
import json
from pathlib import Path


def validate_event_system(project_root, logger=None):
    """
    Validate the event system configuration.
    
    Returns:
        {
            'valid': bool,
            'errors': list,
            'event_count': int,
            'handler_count': int,
            'mapping_count': int
        }
    """
    errors = []
    
    config_dir = os.path.join(project_root, "orbiter", "config")
    
    # 1. Load event_types_list.json
    event_types_list_path = os.path.join(config_dir, "event_types_list.json")
    event_types_list = _load_json(event_types_list_path, "event_types_list", errors)
    
    # 2. Load handlers_list.json
    handlers_list_path = os.path.join(config_dir, "handlers_list.json")
    handlers_list = _load_json(handlers_list_path, "handlers_list", errors)
    
    # 3. Load event_types_structure.json
    structure_path = os.path.join(config_dir, "event_types_structure.json")
    event_types_structure = _load_json(structure_path, "event_types_structure", errors)
    
    # 4. Load event_handler_mapping.json
    mapping_path = os.path.join(config_dir, "event_handler_mapping.json")
    event_handler_mapping = _load_json(mapping_path, "event_handler_mapping", errors)
    
    if errors:
        return {'valid': False, 'errors': errors, 'event_count': 0, 'handler_count': 0, 'mapping_count': 0}
    
    event_types = event_types_list.get('eventTypes', [])
    handlers = handlers_list.get('handlers', [])
    mapping = event_handler_mapping.get('mapping', {})
    structure = event_types_structure.get('eventTypes', {})
    
    # 5. Validate: event types in list must exist in structure
    for evt in event_types:
        if evt not in structure:
            errors.append(f"Event type '{evt}' in event_types_list.json but not defined in event_types_structure.json")
    
    # 6. Validate: mapping keys must be in event_types_list
    for evt in mapping.keys():
        if evt not in event_types:
            errors.append(f"Event type '{evt}' in mapping but not in event_types_list.json")
    
    # 7. Validate: handlers in mapping must exist in handlers_list
    for evt, mapping_data in mapping.items():
        mapped_handlers = mapping_data.get('handlers', [])
        for h in mapped_handlers:
            if h not in handlers:
                errors.append(f"Handler '{h}' in mapping['{evt}'] but not in handlers_list.json")
    
    # 8. Validate: each event in mapping has required fields per structure
    for evt, mapping_data in mapping.items():
        if evt in structure:
            mandatory_fields = structure[evt].get('mandatory', [])
            if not mandatory_fields:
                errors.append(f"Event type '{evt}' has no mandatory fields defined in structure")
        else:
            errors.append(f"Event type '{evt}' in mapping but not in structure")
    
    # 9. Validate: structure events that are NOT in mapping (warning only)
    unmapped_events = set(structure.keys()) - set(mapping.keys())
    if unmapped_events:
        if logger:
            logger.warning(f"⚠️ Events in structure but not mapped: {unmapped_events}")
    
    # 10. Validate: handlers that are NOT used in any mapping (warning only)
    used_handlers = set()
    for mapping_data in mapping.values():
        used_handlers.update(mapping_data.get('handlers', []))
    unused_handlers = set(handlers) - used_handlers
    if unused_handlers:
        if logger:
            logger.warning(f"⚠️ Handlers defined but not used: {unused_handlers}")
    
    result = {
        'valid': len(errors) == 0,
        'errors': errors,
        'event_count': len(event_types),
        'handler_count': len(handlers),
        'mapping_count': len(mapping)
    }
    
    if logger and result['valid']:
        logger.debug(f"✅ Event system valid: {result['event_count']} events, {result['handler_count']} handlers, {result['mapping_count']} mappings")
    
    return result


def _load_json(path, name, errors):
    """Helper to load a JSON file, append error if fails."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        errors.append(f"Missing required file: {path}")
        return {}
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in {name}: {e}")
        return {}


# CLI test
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from orbiter.utils.system import get_project_root
    
    result = validate_event_system(get_project_root())
    print(f"Valid: {result['valid']}")
    if result['errors']:
        print("Errors:")
        for e in result['errors']:
            print(f"  - {e}")
    print(f"Events: {result['event_count']}, Handlers: {result['handler_count']}, Mappings: {result['mapping_count']}")