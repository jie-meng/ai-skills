# Confluence REST API Reference

> **Official docs (v2)**: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/
> **OpenAPI spec**: https://dac-static.atlassian.com/cloud/confluence/openapi-v2.v3.json

Base URL: `https://yoursite.atlassian.net/wiki/api/v2`

**Authentication** (Basic auth for scripts and bots):
```
Authorization: Basic base64(email:api_token)
```

All requests should include `Accept: application/json`. Write requests also need `Content-Type: application/json`.

The v2 API uses cursor-based pagination (no offset) and does not support `expand` — fetch related data via separate endpoints.

---

## Pages

### `GET /wiki/api/v2/pages/{id}`

Returns a single page.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `body-format` | string | `storage`, `atlas_doc_format`, or `view` |
| `get-draft` | boolean | Return draft version if available |
| `version` | integer | Specific version number |
| `include-labels` | boolean | Include labels |
| `include-properties` | boolean | Include content properties |
| `include-versions` | boolean | Include version history |

**Response** (key fields)

```json
{
  "id": "12345",
  "status": "current",
  "title": "Page Title",
  "spaceId": "98765",
  "parentId": "11111",
  "parentType": "page",
  "authorId": "5b10ac...",
  "createdAt": "2025-01-15T10:00:00.000Z",
  "version": {
    "createdAt": "2025-01-16T14:30:00.000Z",
    "message": "Updated intro",
    "number": 3,
    "minorEdit": false,
    "authorId": "5b10ac..."
  },
  "body": {
    "storage": {
      "representation": "storage",
      "value": "<p>Page content in storage format</p>"
    }
  },
  "_links": {
    "webui": "/spaces/TEAM/pages/12345/Page+Title",
    "editui": "/pages/resumedraft.action?draftId=12345",
    "base": "https://yoursite.atlassian.net/wiki"
  }
}
```

---

### `GET /wiki/api/v2/pages`

Returns all pages (paginated).

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | array | Filter by page IDs |
| `space-id` | array | Filter by space IDs |
| `title` | string | Filter by exact title |
| `status` | array | `current`, `draft`, `trashed` |
| `body-format` | string | Body format to return |
| `sort` | string | Sort order (e.g. `-modified-date`) |
| `cursor` | string | Pagination cursor |
| `limit` | integer | Max results (default: 25) |

---

### `GET /wiki/api/v2/spaces/{id}/pages`

Returns pages in a specific space.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `depth` | string | `root` for top-level only, `all` for all pages |
| `title` | string | Filter by exact title |
| `status` | array | `current`, `draft`, `trashed` |
| `body-format` | string | Body format to return |
| `sort` | string | Sort order |
| `cursor` | string | Pagination cursor |
| `limit` | integer | Max results |

---

### `POST /wiki/api/v2/pages`

Creates a new page.

**Request body**

```json
{
  "spaceId": "98765",
  "status": "current",
  "title": "New Page",
  "parentId": "11111",
  "body": {
    "representation": "storage",
    "value": "<p>Page content here</p>"
  }
}
```

**Response**: `200 OK` — returns the created page object.

---

### `PUT /wiki/api/v2/pages/{id}`

Updates an existing page. Must include current version number + 1.

**Request body**

```json
{
  "id": "12345",
  "status": "current",
  "title": "Updated Title",
  "body": {
    "representation": "storage",
    "value": "<p>Updated content</p>"
  },
  "version": {
    "number": 4,
    "message": "Fixed typos"
  }
}
```

**Response**: `200 OK` — returns the updated page object.

---

### `DELETE /wiki/api/v2/pages/{id}`

Deletes a page (moves to trash by default).

| Parameter | Type | Description |
|-----------|------|-------------|
| `purge` | boolean | Permanently delete (skip trash) |
| `draft` | boolean | Delete a draft page |

**Response**: `204 No Content`

---

## Spaces

### `GET /wiki/api/v2/spaces`

Returns all spaces.

| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | string | `global` or `personal` |
| `status` | string | `current` or `archived` |
| `keys` | array | Filter by space keys |
| `sort` | string | Sort order |
| `cursor` | string | Pagination cursor |
| `limit` | integer | Max results |

**Response**

```json
{
  "results": [
    {
      "id": "98765",
      "key": "TEAM",
      "name": "Team Space",
      "type": "global",
      "status": "current",
      "_links": {
        "webui": "/spaces/TEAM"
      }
    }
  ],
  "_links": {
    "next": "...",
    "base": "https://yoursite.atlassian.net/wiki"
  }
}
```

---

## Comments

### `GET /wiki/api/v2/pages/{id}/footer-comments`

Returns footer comments on a page.

| Parameter | Type | Description |
|-----------|------|-------------|
| `body-format` | string | `storage`, `atlas_doc_format`, or `view` |
| `sort` | string | Sort order |
| `cursor` | string | Pagination cursor |
| `limit` | integer | Max results |

### `POST /wiki/api/v2/footer-comments`

Adds a footer comment to a page.

**Request body**

```json
{
  "pageId": "12345",
  "body": {
    "representation": "storage",
    "value": "<p>Comment text</p>"
  }
}
```

**Response**: `200 OK` — returns the comment object.

---

## Labels

### `GET /wiki/api/v2/pages/{id}/labels`

Returns labels on a page.

### `POST /wiki/api/v2/pages/{id}/labels`

Adds labels to a page.

**Request body**

```json
[
  { "name": "architecture" },
  { "name": "backend" }
]
```

**Response**: `200 OK`

---

## Children

### `GET /wiki/api/v2/pages/{id}/children`

Returns child pages.

| Parameter | Type | Description |
|-----------|------|-------------|
| `cursor` | string | Pagination cursor |
| `limit` | integer | Max results |
| `sort` | string | Sort order |

---

## Search (CQL) — v1 API

Search uses the v1 REST API endpoint.

### `GET /wiki/rest/api/search`

| Parameter | Type | Description |
|-----------|------|-------------|
| `cql` | string | **Required.** CQL query |
| `limit` | integer | Max results (default: 25) |
| `start` | integer | Pagination offset |
| `expand` | string | Expand options |

**Response**

```json
{
  "results": [
    {
      "content": {
        "id": "12345",
        "type": "page",
        "title": "Page Title",
        "space": { "key": "TEAM", "name": "Team Space" },
        "_links": { "webui": "/spaces/TEAM/pages/12345" }
      },
      "title": "Page Title",
      "lastModified": "2025-01-16T14:30:00.000Z"
    }
  ],
  "totalSize": 42,
  "start": 0,
  "limit": 25
}
```

### Common CQL Patterns

| CQL | Purpose |
|-----|---------|
| `space=TEAM AND type=page` | All pages in a space |
| `text ~ 'keyword'` | Full text search |
| `title = 'Exact Title'` | Exact title match |
| `title ~ 'partial'` | Title contains |
| `label = 'my-label'` | Content with label |
| `type=page AND lastModified >= now('-7d')` | Recently modified pages |
| `creator = currentUser()` | Content I created |
| `space=TEAM AND ancestor = 12345` | Pages under a parent |

---

## Confluence Storage Format

Confluence uses an XHTML-based storage format for page bodies. Common elements:

```html
<p>Paragraph text</p>
<h1>Heading 1</h1> to <h6>Heading 6</h6>
<ul><li>Bullet item</li></ul>
<ol><li>Numbered item</li></ol>
<code>Inline code</code>
<strong>Bold</strong>
<em>Italic</em>
<a href="https://example.com">Link</a>
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">python</ac:parameter>
  <ac:plain-text-body><![CDATA[print("hello")]]></ac:plain-text-body>
</ac:structured-macro>
```

For simple content, wrapping text in `<p>` tags is sufficient.

---

## Rate Limits

Confluence Cloud rate limits vary by endpoint. When rate-limited, the API returns `429 Too Many Requests` with a `Retry-After` header.

---

## Error Response Format

```json
{
  "statusCode": 404,
  "data": {
    "authorized": false,
    "valid": true
  },
  "message": "No content found with id: 99999"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request — invalid CQL, malformed body |
| 401 | Authentication failed — check email + token |
| 403 | Permission denied — user lacks required space permission |
| 404 | Not found — page/space doesn't exist |
| 413 | Request entity too large — page body exceeds size limit |
| 429 | Rate limited — back off and retry |
