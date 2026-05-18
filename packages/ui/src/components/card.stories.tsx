import type { Meta, StoryObj } from "@storybook/react";

import { Badge } from "./badge";
import { Button } from "./button";
import { Card } from "./card";

const meta: Meta<typeof Card> = {
  title: "Components/Card",
  component: Card,
  tags: ["autodocs"],
};
export default meta;

type Story = StoryObj<typeof Card>;

export const Basic: Story = {
  args: {
    children: (
      <div className="space-y-2">
        <h3 className="text-base font-semibold">Senior Backend Engineer</h3>
        <p className="text-sm text-muted-foreground">
          Acme Corp · Remote · 300–400k ₽/month
        </p>
      </div>
    ),
  },
};

export const WithBadgeAndAction: Story = {
  args: {
    children: (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold">Lead Platform Engineer</h3>
          <Badge text="Match: 92%" tone="brand" />
        </div>
        <p className="text-sm text-muted-foreground">
          Yandex · Hybrid · 500k+ ₽/month
        </p>
        <div className="flex gap-2">
          <Button size="sm">Откликнуться</Button>
          <Button size="sm" variant="ghost">
            Подробнее
          </Button>
        </div>
      </div>
    ),
  },
};
