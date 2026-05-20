import type { ComponentType } from "react";

export interface PluginNavConfig {
  icon: string;
  label_zh: string;
  label_en: string;
  order?: number;
}

export interface PluginManifest {
  name: string;
  route: string;
  component: ComponentType;
  nav?: PluginNavConfig;
}
