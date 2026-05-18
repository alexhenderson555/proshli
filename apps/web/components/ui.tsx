// Thin re-export layer. The authoritative primitives now live in
// `@otklik/ui`; we keep this stub so call sites (`@/components/ui`)
// don't need to change all at once.
//
// New code should import directly from `@otklik/ui`.

export {
  Badge,
  type BadgeProps,
  type BadgeTone,
  Button,
  type ButtonProps,
  Card,
  type CardProps,
  Container,
  type ContainerProps,
  Input,
  type InputProps,
  Select,
  type SelectOption,
  type SelectProps,
  Skeleton,
  type SkeletonProps,
  Textarea,
  type TextareaProps,
} from "@otklik/ui";
