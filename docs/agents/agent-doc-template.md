# [Agent name]

## Purpose
[Brief description of what this agent does]

## Owner/Maintainer
[Name and contact]

## Version
[Semantic version, e.g., 1.0.0]

---

## Implementation Status

### Stage
- [ ] Planned
- [ ] WIP (In Progress)
- [ ] Complete
- [ ] Deprecated
- [ ] Maintenance

### Last Updated
[YYYY.MM.DD] - [short description of update]

### Key Milestones
- [Milestone 1]: [Status]
- [Milestone 2]: [Status]

---

## Agent Characteristics

### Input Types
- [Type 1]: [Description]
- [Type 2]: [Description]

### Output Types
- [Type 1]: [Description]
- [Type 2]: [Description]

### Context & Knowledge Stores
- [Knowledge store 1]: [Purpose and location]
- [Knowledge store 2]: [Purpose and location]

### Memory Model
- **Type**: [Stateless / Session-level / Long-term / Hybrid]
- **Description**: [How memory is managed, what is persisted, retention policy]
- **Storage**: [Where memory is stored, if applicable]

---

## Tool Usage

### Tools Used by This Agent
| Tool Name | Purpose | Required |
|-----------|---------|----------|
| [Tool 1] | [Purpose] | Yes/No |
| [Tool 2] | [Purpose] | Yes/No |

### Capabilities as a Tool
When registered as a tool for other agents:

#### Function Signature
```python
async def [method_name](self, [param1]: [type], [param2]: [type]) -> [return_type]:
    """
    [Brief description]
    
    Args:
        [param1]: [Description]
        [param2]: [Description]
    
    Returns:
        [Description of return value]
    """
```

#### Tool Registration Details
- **Tool ID**: [Unique identifier for tool registry]
- **Handler Method**: [Method name agents call]
- **Required Parameters**: [List of required parameters]
- **Optional Parameters**: [List of optional parameters with defaults]
- **Return Format**: [JSON schema or description]

### Usage Examples

#### Example 1: [Scenario]
```
Input: [Example input]
Output: [Example output]
```

#### Example 2: [Scenario]
```
Input: [Example input]
Output: [Example output]
```

---

## Dependencies

### Python Packages
- [Package 1]: [Version/constraint]
- [Package 2]: [Version/constraint]

### External Services
- [Service 1]: [Purpose, required configuration]
- [Service 2]: [Purpose, required configuration]

### Other Agents
- [Agent 1]: [Purpose of dependency]
- [Agent 2]: [Purpose of dependency]

---

## Configuration

### Environment Variables
```
[VAR_NAME]=[default value or description]
[VAR_NAME2]=[default value or description]
```

### Config File Settings
```yaml
[section]:
  [key]: [default_value]
  [key2]: [default_value]
```

### Default Behavior
- [Default behavior 1]
- [Default behavior 2]

---

## Integration

### Coordinator Handoff
**When coordinator routes to this agent:**
- Receives: [What the coordinator passes]
- Expected behavior: [How agent should process input]
- Returns to coordinator: [Format and content]

### Error Handling
- **Timeout behavior**: [What happens on timeout]
- **Invalid input**: [How agent handles invalid input]
- **External service failure**: [Fallback or error reporting]

### Logging & Observability
- **Log level**: [DEBUG, INFO, WARNING, ERROR]
- **Key log points**: [What is logged and where]
- **Metrics**: [Any metrics or tracing points]

---

## Dev Notes

---

## Troubleshooting

### Common Issues & Solutions
| Issue | Solution |
|-------|----------|
| [Issue description] | [Solution steps] |
| [Issue description] | [Solution steps] |

### Debugging Tips
- [Tip 1]
- [Tip 2]

### Performance Considerations
- [Consideration 1]
- [Consideration 2]

---

## References

### Related Documentation
- [Link to related doc]: [Brief description]
- [Link to related doc]: [Brief description]

### Code Files
- [File path]: [What it contains]
- [File path]: [What it contains]