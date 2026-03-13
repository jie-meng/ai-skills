# Jira REST API Reference

> **Official docs**: https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/
> **OpenAPI spec**: https://dac-static.atlassian.com/cloud/jira/platform/swagger-v3.v3.json

Base URL: `https://yoursite.atlassian.net/rest/api/3`

**Authentication** (Basic auth for scripts and bots):
```
Authorization: Basic base64(email:api_token)
```

All requests should include `Accept: application/json`. Write requests also need `Content-Type: application/json`.

---

## Core Endpoints

### Issues

#### `GET /rest/api/3/issue/{issueIdOrKey}`

Returns a single issue with all fields.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `fields` | string | Comma-separated field names to return (e.g. `summary,status,assignee`) |
| `expand` | string | Extra data to include (e.g. `renderedFields,changelog`) |

**Response** (key fields)

```json
{
  "key": "PROJ-123",
  "self": "https://yoursite.atlassian.net/rest/api/3/issue/10001",
  "fields": {
    "summary": "Fix login timeout",
    "status": { "name": "In Progress", "statusCategory": { "name": "In Progress" } },
    "issuetype": { "name": "Bug" },
    "priority": { "name": "High" },
    "assignee": { "accountId": "5b10ac...", "displayName": "Jane Doe" },
    "reporter": { "accountId": "5b10ac...", "displayName": "John Smith" },
    "labels": ["backend", "urgent"],
    "components": [{ "name": "Auth" }],
    "fixVersions": [{ "name": "v2.1" }],
    "description": { "type": "doc", "version": 1, "content": [...] },
    "created": "2025-01-15T10:00:00.000+0000",
    "updated": "2025-01-16T14:30:00.000+0000",
    "parent": { "key": "PROJ-100", "fields": { "summary": "Epic name" } },
    "subtasks": [{ "key": "PROJ-124", "fields": { "summary": "...", "status": { "name": "..." } } }],
    "issuelinks": [{ "type": { "outward": "blocks" }, "outwardIssue": { "key": "PROJ-125" } }],
    "comment": { "total": 3, "comments": [...] }
  }
}
```

---

#### `POST /rest/api/3/issue`

Creates a new issue.

**Request body**

```json
{
  "fields": {
    "project": { "key": "PROJ" },
    "summary": "Issue title",
    "issuetype": { "name": "Bug" },
    "priority": { "name": "High" },
    "assignee": { "accountId": "5b10ac..." },
    "labels": ["backend"],
    "description": {
      "version": 1,
      "type": "doc",
      "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "Details here" }] }]
    },
    "parent": { "key": "PROJ-100" },
    "components": [{ "name": "Auth" }]
  }
}
```

**Response**: `201 Created`

```json
{ "id": "10001", "key": "PROJ-123", "self": "https://..." }
```

---

#### `PUT /rest/api/3/issue/{issueIdOrKey}`

Edits an issue. Only include fields you want to update.

**Request body**: Same `fields` object as create, but only changed fields.

**Response**: `204 No Content`

---

#### `DELETE /rest/api/3/issue/{issueIdOrKey}`

Deletes an issue.

| Parameter | Type | Description |
|-----------|------|-------------|
| `deleteSubtasks` | boolean | Delete subtasks too (default: false) |

**Response**: `204 No Content`

---

### Assignee

#### `PUT /rest/api/3/issue/{issueIdOrKey}/assignee`

**Request body**

```json
{ "accountId": "5b10ac..." }
```

Set `accountId` to `null` to unassign. Set to `"-1"` for automatic/default assignee.

**Response**: `204 No Content`

---

### Transitions

#### `GET /rest/api/3/issue/{issueIdOrKey}/transitions`

Returns available transitions for an issue.

**Response**

```json
{
  "transitions": [
    { "id": "31", "name": "Start Progress", "to": { "name": "In Progress", "id": "3" } },
    { "id": "41", "name": "Done", "to": { "name": "Done", "id": "4" } }
  ]
}
```

#### `POST /rest/api/3/issue/{issueIdOrKey}/transitions`

Transitions an issue to a new status.

**Request body**

```json
{
  "transition": { "id": "31" },
  "update": {
    "comment": [{
      "add": {
        "body": { "version": 1, "type": "doc", "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "Starting work" }] }] }
      }
    }]
  },
  "fields": {
    "resolution": { "name": "Fixed" }
  }
}
```

**Response**: `204 No Content`

---

### Comments

#### `GET /rest/api/3/issue/{issueIdOrKey}/comment`

| Parameter | Type | Description |
|-----------|------|-------------|
| `startAt` | int | Pagination offset |
| `maxResults` | int | Max comments to return |
| `orderBy` | string | `-created` or `+created` |

**Response**

```json
{
  "comments": [
    {
      "id": "10001",
      "author": { "displayName": "Jane Doe", "accountId": "5b10ac..." },
      "body": { "type": "doc", "version": 1, "content": [...] },
      "created": "2025-01-15T10:00:00.000+0000",
      "updated": "2025-01-15T10:00:00.000+0000"
    }
  ],
  "total": 3,
  "startAt": 0,
  "maxResults": 50
}
```

#### `POST /rest/api/3/issue/{issueIdOrKey}/comment`

**Request body**

```json
{
  "body": {
    "version": 1,
    "type": "doc",
    "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "Comment text" }] }]
  }
}
```

**Response**: `201 Created` — returns the comment object.

---

### Search (JQL)

#### `GET /rest/api/3/search/jql`

| Parameter | Type | Description |
|-----------|------|-------------|
| `jql` | string | **Required.** JQL query |
| `maxResults` | int | Max results (default: 50) |
| `fields` | string | Comma-separated field names |
| `expand` | string | Expand options |
| `nextPageToken` | string | Pagination token |

**Response**

```json
{
  "issues": [
    { "key": "PROJ-123", "fields": { "summary": "...", "status": { "name": "..." }, ... } }
  ],
  "total": 42,
  "maxResults": 50
}
```

> Note: The legacy `/rest/api/3/search` endpoint has been removed from Jira Cloud. Use `/rest/api/3/search/jql` instead.

---

### Issue Links

#### `POST /rest/api/3/issueLink`

**Request body**

```json
{
  "type": { "name": "Blocks" },
  "inwardIssue": { "key": "PROJ-456" },
  "outwardIssue": { "key": "PROJ-123" }
}
```

Common link types: `Blocks`, `Cloners`, `Duplicate`, `Relates`

**Response**: `201 Created`

---

### Current User

#### `GET /rest/api/3/myself`

**Response**

```json
{
  "accountId": "5b10ac...",
  "emailAddress": "you@example.com",
  "displayName": "Jane Doe",
  "active": true
}
```

---

### Projects

#### `GET /rest/api/3/project`

Returns all projects visible to the user.

| Parameter | Type | Description |
|-----------|------|-------------|
| `maxResults` | int | Max results |
| `startAt` | int | Pagination offset |

---

## Agile REST API (Sprints & Boards)

Base URL: `https://yoursite.atlassian.net/rest/agile/1.0`

Uses the same Basic auth as the platform API.

### Boards

#### `GET /rest/agile/1.0/board`

| Parameter | Type | Description |
|-----------|------|-------------|
| `projectKeyOrId` | string | Filter by project |
| `maxResults` | int | Max results |

**Response**

```json
{
  "values": [
    { "id": 42, "name": "PROJ board", "type": "scrum", "location": { "projectKey": "PROJ" } }
  ]
}
```

### Sprints

#### `GET /rest/agile/1.0/board/{boardId}/sprint`

| Parameter | Type | Description |
|-----------|------|-------------|
| `state` | string | `active`, `closed`, `future` (comma-separated) |

**Response**

```json
{
  "values": [
    { "id": 123, "name": "Sprint 10", "state": "active", "startDate": "...", "endDate": "..." }
  ]
}
```

### Sprint Issues

#### `GET /rest/agile/1.0/sprint/{sprintId}/issue`

| Parameter | Type | Description |
|-----------|------|-------------|
| `maxResults` | int | Max results |
| `fields` | string | Comma-separated field names |
| `jql` | string | Additional JQL filter |

**Response**: Same structure as `/search/jql`.

---

## Atlassian Document Format (ADF)

API v3 uses ADF for rich text fields (`description`, `comment.body`, `environment`). A minimal document:

```json
{
  "version": 1,
  "type": "doc",
  "content": [
    {
      "type": "paragraph",
      "content": [
        { "type": "text", "text": "Hello world" }
      ]
    }
  ]
}
```

Common node types: `paragraph`, `heading` (with `attrs.level`), `bulletList`, `orderedList`, `listItem`, `codeBlock` (with `attrs.language`), `blockquote`, `table`, `tableRow`, `tableCell`, `mention`, `hardBreak`, `text`.

Text nodes support marks: `strong`, `em`, `code`, `underline`, `strike`, `link` (with `attrs.href`).

---

## Rate Limits

Jira Cloud rate limits vary by endpoint tier and plan. When rate-limited, the API returns `429 Too Many Requests` with a `Retry-After` header.

---

## Error Response Format

```json
{
  "errorMessages": ["Issue does not exist or you do not have permission to see it."],
  "errors": {}
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request — invalid fields, unknown issue type, malformed JQL |
| 401 | Authentication failed — check email + token |
| 403 | Permission denied — user lacks required project permission |
| 404 | Not found — issue/project/board doesn't exist |
| 429 | Rate limited — back off and retry |
