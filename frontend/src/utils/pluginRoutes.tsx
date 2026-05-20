import { lazy, Suspense, useState, useEffect } from "react";
import { NavLink, Route } from "react-router-dom";
import { useTranslation } from "react-i18next";
import * as TablerIcons from "@tabler/icons-react";

import type { PluginManifest } from "../types/plugin";

// ── 在此处注册插件 ──
// 每新增一个插件，添加一行 lazy import
const pluginModules: Record<string, () => Promise<{ default: PluginManifest }>> = {
  // hello: () => import("../../plugins/_example_hello/frontend/index"),
};

// 缓存已解析的插件列表
let _resolved: PluginManifest[] | null = null;

async function getPlugins(): Promise<PluginManifest[]> {
  if (_resolved) return _resolved;
  const results = await Promise.all(
    Object.entries(pluginModules).map(([, loader]) => loader().then((m) => m.default)),
  );
  _resolved = results;
  return results;
}

// ── 路由元素（用于 App.tsx） ──
export function loadPluginRoutes() {
  const plugins = Object.entries(pluginModules).map(([key, loader]) => {
    const Component = lazy(() => loader().then((m) => ({ default: m.default.component })));
    return { key, Component };
  });

  return plugins.map(({ key, Component }) => (
    <Route
      key={key}
      path={`plugins/${key}`}
      element={
        <Suspense fallback={<div style={{ padding: 24, color: "var(--text-tertiary)" }}>Loading...</div>}>
          <Component />
        </Suspense>
      }
    />
  ));
}

// ── 侧边栏导航项（用于 Layout.tsx） ──
export function PluginNavItems() {
  const { i18n } = useTranslation();
  const [plugins, setPlugins] = useState<PluginManifest[]>([]);

  useEffect(() => {
    getPlugins().then(setPlugins);
  }, []);

  if (plugins.length === 0) return null;

  const sorted = [...plugins].sort((a, b) => (a.nav?.order ?? 100) - (b.nav?.order ?? 100));

  return (
    <>
      {sorted.map((plugin) => {
        const lang = i18n.language?.startsWith("zh") ? "zh" : "en";
        const label = plugin.nav
          ? lang === "zh"
            ? plugin.nav.label_zh
            : plugin.nav.label_en
          : plugin.name;
        const iconName = plugin.nav?.icon || "IconPuzzle";
        // @ts-expect-error — dynamic Tabler icon lookup
        const IconComp = TablerIcons[iconName] || TablerIcons.IconPuzzle;

        return (
          <NavLink
            key={plugin.name}
            to={plugin.route}
            className={({ isActive }) =>
              `sidebar-item ${isActive ? "active" : ""}`
            }
          >
            <IconComp size={16} stroke={1.5} />
            <span>{label}</span>
          </NavLink>
        );
      })}
    </>
  );
}
