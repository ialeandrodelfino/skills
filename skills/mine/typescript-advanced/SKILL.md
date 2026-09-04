---
name: typescript-advanced
description: Master TypeScript's advanced type system including generics, conditional types, mapped types, template literals, and utility types for building type-safe applications. Use when implementing complex type logic, creating reusable type utilities, or ensuring compile-time type safety in TypeScript projects. Don't use for plain JavaScript, runtime validation libraries (Zod, Yup), or basic TypeScript syntax questions.
metadata:
  author: Pedro Nauck
  github: https://github.com/pedronauck
  repository: https://github.com/pedronauck/skills
---
# TypeScript Advanced Types

Use this skill when generic inference, conditional/mapped types, template literals, or a reusable type utility is the actual problem. Ordinary typed API, form, and state work uses its domain guidance unless advanced type behavior needs attention.

| Concern being changed | Reference |
| --- | --- |
| Generics, conditional/mapped/template-literal and utility types | `references/core-concepts.md` |
| Reusable emitters, builders, clients, deep utilities, or discriminated models | `references/advanced-patterns.md` |
| `infer`, narrowing, assertion functions, and type-contract tests | `references/type-inference.md` |
| Compiler configuration, type complexity, and maintainability | `references/best-practices.md` |

Prefer the simplest type that expresses the contract. Use `unknown` and real narrowing at untrusted boundaries; preserve discriminants and readonly intent. Let inference handle local values and follow repository conventions for public annotations, `interface`, and `type`.

Use the existing `tsconfig`; reference configurations are examples, not instructions to change it. Add compile-time tests only when type behavior is a product/library contract, using its owning suite. Avoid a new type framework or elaborate generic abstraction for a single ordinary call site. Run the repository's affected typecheck gate.
