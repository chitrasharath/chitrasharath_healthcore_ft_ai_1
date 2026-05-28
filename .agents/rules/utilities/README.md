# Utilities Rules (7)
1. Implement business logic in TypeScript with strict typing for all entities.
2. Keep calculations and transformations pure and deterministic.
3. Validate data before processing or aggregation.
4. Separate utility concerns into focused modules (collections, search, transformations, validations).
5. Ensure logic is testable and verified with lightweight checks where applicable.
6. All utility modules and functions must be exported and accessible for import and use in frontend application files (e.g., Next.js pages/components).
7. Frontend flows must reuse these utility functions instead of duplicating business logic in UI components.