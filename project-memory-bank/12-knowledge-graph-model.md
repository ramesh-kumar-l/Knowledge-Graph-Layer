# 12 — Knowledge Graph Model (Taxonomies)

**Status:** Phase 1 — complete (2026-06-23).

All entity and relationship types extend the base objects in `10-domain-model.md`.

---

## Entity taxonomy (12 types)

### PERSON
A human individual — user, contact, collaborator, author.
```
attributes: {
  email?:         String
  role?:          String
  orgId?:         UUID          → ORGANIZATION
  skillIds?:      UUID[]        → SKILL entities
  externalIds?:   Map<String,String>   -- GitHub handle, LinkedIn, etc.
}
```

### PROJECT
A structured initiative with goals, tasks, and team members.
```
attributes: {
  status:         "ACTIVE" | "PAUSED" | "COMPLETED" | "ARCHIVED"
  startDate?:     Date
  endDate?:       Date
  description?:   String
  repository?:    String       -- VCS URL
  tags?:          String[]
}
```

### GOAL
A desired outcome or objective, possibly nested under another Goal.
```
attributes: {
  status:           "OPEN" | "IN_PROGRESS" | "COMPLETED" | "ABANDONED"
  priority?:        "HIGH" | "MEDIUM" | "LOW"
  dueDate?:         Date
  successCriteria?: String[]
}
```

### TASK
An actionable unit of work, potentially assigned to a Person.
```
attributes: {
  status:         "TODO" | "IN_PROGRESS" | "DONE" | "BLOCKED"
  assigneeId?:    UUID         → PERSON
  dueDate?:       Date
  estimateHours?: Float
}
```

### SKILL
A capability, competency, or area of expertise.
```
attributes: {
  domain?:        String       -- "engineering", "design", "management"
  level?:         "BEGINNER" | "INTERMEDIATE" | "EXPERT"
  verified?:      Boolean
}
```

### DOCUMENT
A file, note, or textual artifact.
```
attributes: {
  mimeType?:      String
  uri?:           String
  contentHash?:   String       -- SHA-256
  wordCount?:     Int
  language?:      String       -- ISO 639-1
}
```

### ORGANIZATION
A company, team, department, or community.
```
attributes: {
  orgType?:       "COMPANY" | "TEAM" | "DEPARTMENT" | "COMMUNITY"
  website?:       String
  parentId?:      UUID         → ORGANIZATION (nested orgs)
}
```

### EVENT
A time-bound occurrence: meeting, release, incident, milestone.
```
attributes: {
  startTime?:     Timestamp
  endTime?:       Timestamp
  eventType?:     String
  locationId?:    UUID         → LOCATION
  recurring?:     Boolean
}
```

### CONCEPT
An abstract idea, domain, body of knowledge, or named topic.
```
attributes: {
  domain?:        String
  definition?:    String
  externalUri?:   String       -- Wikidata, schema.org link
}
```

### ARTIFACT
A technical output: code file, dataset, model, binary, API spec.
```
attributes: {
  artifactType?:  "CODE" | "DATASET" | "MODEL" | "API" | "BINARY" | "CONFIG"
  version?:       String
  uri?:           String
  contentHash?:   String
  language?:      String
}
```

### LOCATION
A physical or virtual place.
```
attributes: {
  locationType?:  "PHYSICAL" | "VIRTUAL" | "GEOGRAPHIC"
  address?:       String
  coordinates?:   { lat: Float, lon: Float }
  timezone?:      String
  url?:           String       -- for virtual locations
}
```

### PRODUCT
A deliverable, service, or software product.
```
attributes: {
  productType?:   "SOFTWARE" | "SERVICE" | "API" | "PLATFORM" | "DATASET"
  version?:       String
  status?:        "ALPHA" | "BETA" | "GA" | "DEPRECATED"
  ownerId?:       UUID         → ORGANIZATION | PERSON
}
```

---

## Relationship taxonomy (36 types across 8 categories)

### IDENTITY — resolve multiple references to the same real-world thing
| Type | Meaning | Direction |
|------|---------|-----------|
| IS_SAME_AS | Two entities are the same real-world thing | BIDIRECTIONAL |
| IS_ALIAS_OF | One name/ID aliases another | DIRECTED |
| IS_VARIATION_OF | A variant or fork of another entity | DIRECTED |

### OWNERSHIP — attribution and possession
| Type | Meaning | Direction |
|------|---------|-----------|
| OWNS | Entity owns or holds another | DIRECTED |
| CREATED_BY | Entity was created by Person/Agent | DIRECTED |
| MAINTAINED_BY | Entity is actively maintained by | DIRECTED |
| AUTHORED_BY | Document/Artifact authored by Person | DIRECTED |

### DEPENDENCY — technical and logical dependencies
| Type | Meaning | Direction |
|------|---------|-----------|
| DEPENDS_ON | Entity requires another to function | DIRECTED |
| REQUIRES | Hard requirement (fails without) | DIRECTED |
| USES | Soft dependency / integration | DIRECTED |
| INTEGRATES_WITH | Peer-level integration | BIDIRECTIONAL |

### HIERARCHY — containment and parent-child
| Type | Meaning | Direction |
|------|---------|-----------|
| PART_OF | Component of a larger entity | DIRECTED |
| CONTAINS | Inverse of PART_OF | DIRECTED |
| CHILD_OF | Hierarchical child | DIRECTED |
| PARENT_OF | Hierarchical parent | DIRECTED |

### TEMPORAL — time-based ordering and co-occurrence
| Type | Meaning | Direction |
|------|---------|-----------|
| PRECEDED_BY | Came before another entity/event | DIRECTED |
| FOLLOWED_BY | Came after | DIRECTED |
| CO_OCCURRED_WITH | Happened at the same time | BIDIRECTIONAL |
| SCHEDULED_ON | Associated with a time/event | DIRECTED |

### GOAL — objective and progress relationships
| Type | Meaning | Direction |
|------|---------|-----------|
| WORKS_TOWARD | Task/Project works toward a Goal | DIRECTED |
| CONTRIBUTES_TO | Partial contribution to an objective | DIRECTED |
| BLOCKS | Prevents progress of another | DIRECTED |
| ENABLES | Creates conditions for another | DIRECTED |

### PROJECT — team and project participation
| Type | Meaning | Direction |
|------|---------|-----------|
| ASSIGNED_TO | Task assigned to Person | DIRECTED |
| MEMBER_OF | Person belongs to Project/Organization | DIRECTED |
| REPORTS_TO | Person reports to another Person | DIRECTED |
| COLLABORATES_ON | Peer-level collaboration | BIDIRECTIONAL |

### SEMANTIC — conceptual associations
| Type | Meaning | Direction |
|------|---------|-----------|
| RELATED_TO | General semantic relatedness | BIDIRECTIONAL |
| SIMILAR_TO | High semantic/functional similarity | BIDIRECTIONAL |
| CONTRADICTS | Assertions are in conflict | BIDIRECTIONAL |
| REFERENCES | One entity cites/links to another | DIRECTED |
| DERIVED_FROM | Built from or based on another | DIRECTED |

---

## Key entity-type constraints

Not all relationships are valid between all entity types. Critical constraints:

| Relationship | Valid from | Valid to |
|-------------|------------|---------|
| ASSIGNED_TO | TASK | PERSON |
| AUTHORED_BY | DOCUMENT, ARTIFACT | PERSON |
| WORKS_TOWARD | TASK, PROJECT | GOAL |
| REPORTS_TO | PERSON | PERSON |
| IS_SAME_AS | Any type | Same type only |
| DEPENDS_ON | ARTIFACT, PRODUCT, PROJECT | ARTIFACT, PRODUCT, PROJECT |
| MEMBER_OF | PERSON | PROJECT, ORGANIZATION |
| PART_OF | Any | Any (same or parent type preferred) |

Full constraint matrix is formalized in ADR-0002 (`docs/adr/ADR-0002-relationship-typing.md`).
