// Hand-written cross-cutting types that don't belong to a single endpoint.
//
// Once Wave 9's codegen runs against a live OpenAPI doc, prefer the
// generated equivalents from `./openapi`. This file is a stable seam for
// types we want guaranteed even when codegen is offline (e.g. the
// `ApiError` envelope shipped by the global exception handler).

export interface ApiError {
  detail: string;
  request_id?: string;
}

export type SortOrder = "asc" | "desc";
