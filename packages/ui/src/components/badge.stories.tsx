import type { Meta, StoryObj } from "@storybook/react";

import { Badge, type BadgeTone } from "./badge";

const meta: Meta<typeof Badge> = {
  title: "Components/Badge",
  component: Badge,
  tags: ["autodocs"],
  argTypes: {
    tone: {
      control: "select",
      options: ["neutral", "brand", "accent", "success", "warning", "danger"],
    },
    text: { control: "text" },
  },
  args: {
    text: "Match: 92%",
    tone: "brand",
  },
};
export default meta;

type Story = StoryObj<typeof Badge>;

export const Brand: Story = {};

export const AllTones: Story = {
  render: () => {
    const tones: { tone: BadgeTone; label: string }[] = [
      { tone: "neutral", label: "Draft" },
      { tone: "brand", label: "Match: 92%" },
      { tone: "accent", label: "Featured" },
      { tone: "success", label: "Applied" },
      { tone: "warning", label: "Expiring" },
      { tone: "danger", label: "Rejected" },
    ];
    return (
      <div className="flex flex-wrap gap-2">
        {tones.map(({ tone, label }) => (
          <Badge key={tone} tone={tone} text={label} />
        ))}
      </div>
    );
  },
};
