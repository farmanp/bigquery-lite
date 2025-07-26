# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for BigQuery-Lite, documenting important architectural decisions made during the project's development.

## What are ADRs?

Architecture Decision Records (ADRs) are documents that capture important architectural decisions made along with their context and consequences. They serve as a historical record of why certain technical choices were made.

## Format

We use the [MADR (Markdown Architecture Decision Records)](https://adr.github.io/madr/) format for our ADRs.

Each ADR includes:

- **Status**: Proposed, Accepted, Rejected, Deprecated, or Superseded
- **Context**: The situation that prompted this decision
- **Decision**: The architectural decision we made
- **Rationale**: Why we made this decision
- **Consequences**: The positive and negative outcomes

## Current ADRs

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-dual-engine-architecture.md) | Dual Engine Architecture (DuckDB + ClickHouse) | Accepted | 2024-01-26 |

## Creating New ADRs

When making significant architectural decisions:

1. **Create a new ADR file**: `NNNN-short-title.md` (e.g., `0002-api-framework-choice.md`)
2. **Use the MADR template** (see template below)
3. **Number sequentially** starting from 0001
4. **Update this README** with the new ADR entry

### ADR Template

```markdown
# ADR-NNNN: [Short Title]

## Status

[Proposed | Accepted | Rejected | Deprecated | Superseded by ADR-XXXX]

## Context

[Describe the situation that prompted this decision]

## Decision

[State the architectural decision made]

## Rationale

[Explain why this decision was made]

## Consequences

### Positive
- [List positive outcomes]

### Negative  
- [List negative outcomes or trade-offs]

### Risks and Mitigations
- **Risk**: [Describe risk]
- **Mitigation**: [How to address it]

## Alternatives Considered

[List other options that were considered and why they were rejected]

## Related Decisions

- [Link to related ADRs]

## References

- [External references that influenced this decision]

---

**Date**: YYYY-MM-DD  
**Author**: [Author Name]  
**Reviewers**: [Reviewer Names]
```

## Guidelines for ADRs

### When to Write an ADR

Create an ADR for decisions that:

- **Impact system architecture**: Database choices, framework selections, deployment strategies
- **Have long-term consequences**: Hard to reverse or change later
- **Involve trade-offs**: Multiple viable options with different pros/cons
- **Affect multiple teams**: Decisions that impact how others work with the system
- **Are controversial**: Decisions where team members have different opinions

### ADR Quality Guidelines

**Good ADRs:**
- Focus on **architectural decisions**, not implementation details
- Explain the **context and constraints** that led to the decision
- Present **alternatives considered** and why they were rejected
- Are **concise but complete** - enough detail to understand the reasoning
- Include **consequences and trade-offs** honestly
- Reference **external sources** that influenced the decision

**Avoid:**
- Implementation details that belong in technical documentation
- Decisions that are easily reversible
- Personal opinions without technical justification
- Incomplete context that makes the decision hard to understand later

## ADR Lifecycle

1. **Proposed**: Initial draft, under discussion
2. **Accepted**: Decision made and implemented
3. **Rejected**: Decision was considered but not adopted
4. **Deprecated**: Decision is no longer relevant
5. **Superseded**: Replaced by a newer ADR

## Tools and Resources

- [MADR Template](https://adr.github.io/madr/)
- [ADR Tools](https://github.com/npryce/adr-tools)
- [Architecture Decision Records Guide](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)

## Questions?

If you have questions about ADRs or need help writing one, please:

1. Review existing ADRs for examples
2. Check the [MADR documentation](https://adr.github.io/madr/)
3. Ask in team discussions or code reviews