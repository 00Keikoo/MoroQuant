# API Specification: [Subsystem / Feature]

## 1. Base URL
`[e.g., /api/v1/subsystem]`

## 2. Endpoints Summary

| Method | Path | Description | Auth Required |
|---|---|---|---|
| `GET` | `/resource` | List items | Yes |
| `POST` | `/resource` | Create a new item | Yes |
| `DELETE` | `/resource/:id` | Remove an item | Yes |

## 3. Endpoint Details

### `GET /resource`
- **Description**: [Details about behavior, pagination, filtering parameters.]
- **Query Parameters**:
  - `limit` (optional): Max items (Default: 50)
- **Response Headers**: `Content-Type: application/json`
- **Response Body (200 OK)**:
```json
{
  "items": [],
  "total": 0
}
```

### `POST /resource`
- **Description**: [Details about state modifications, payloads.]
- **Request Body**:
```json
{
  "name": "string",
  "config": {}
}
```
- **Responses**:
  - `201 Created`: Returns the generated resource.
  - `400 Bad Request`: Validation failure description.
  - `401 Unauthorized`: Missing or invalid credentials.
