/**
 * ProudCopilot - Unified Icon System
 * Using Tabler Icons for consistent, professional iconography
 */

import {
  // Navigation & Branding
  IconRobot,
  IconBrain,
  IconBuildingArch,
  IconBuilding,
  IconWorld,

  // Status & Feedback
  IconAlertCircle,
  IconAlertTriangle,
  IconCheck,
  IconX,
  IconInfoCircle,

  // Time & Date
  IconSun,
  IconSunHigh,
  IconMoon,
  IconCalendar,
  IconClock,
  IconHourglass,

  // Data & Content
  IconChartBar,
  IconChartLine,
  IconFolder,
  IconFile,
  IconFileText,
  IconPaperclip,

  // Actions
  IconTool,
  IconBolt,
  IconSend,
  IconTrash,
  IconEdit,
  IconPlus,
  IconMinus,
  IconRefresh,
  IconCopy,
  IconDownload,
  IconUpload,

  // User & Security
  IconUser,
  IconUsers,
  IconUserStar,
  IconLock,
  IconShield,
  IconKey,

  // Agent Specific
  IconHeartbeat,
  IconDna,
  IconPackage,
  IconCloud,
  IconDatabase,

  // Communication
  IconMessage,
  IconMessages,
  IconListCheck,
  IconPlugConnected,
  IconInbox,

  // UI Controls
  IconBulb,
  IconArrowRight,
  IconChevronDown,
  IconChevronRight,
  IconChevronLeft,
  IconExternalLink,
  IconSearch,
  IconSettings,
  IconLogout,
  IconMenu,
  IconFilter,

  // Status Indicators
  IconCircleCheck,
  IconCircleX,
  IconCircleDot,
  IconLoader2,

  // Features
  IconTarget,
  IconSparkles,
  IconStar,
  IconPin,
  IconPinned,
  IconUnlink,
} from '@tabler/icons-react';

import type { Icon as TablerIcon } from '@tabler/icons-react';

// Icon size presets
export const IconSize = {
  xs: 14,
  sm: 16,
  md: 18,
  lg: 20,
  xl: 24,
} as const;

// Icon stroke width presets
export const IconStroke = {
  light: 1.5,
  regular: 1.75,
  bold: 2,
} as const;

// Named icon exports for semantic usage
export const Icons = {
  // === Navigation & Branding ===
  robot: IconRobot,
  brain: IconBrain,
  building: IconBuildingArch,
  company: IconBuilding,
  world: IconWorld,
  globe: IconWorld,

  // === Status & Feedback ===
  alert: IconAlertCircle,
  warning: IconAlertTriangle,
  success: IconCheck,
  error: IconX,
  info: IconInfoCircle,
  check: IconCheck,

  // === Time & Date ===
  sun: IconSun,
  sunHigh: IconSunHigh,
  moon: IconMoon,
  calendar: IconCalendar,
  clock: IconClock,
  hourglass: IconHourglass,

  // === Data & Content ===
  chart: IconChartBar,
  chartLine: IconChartLine,
  folder: IconFolder,
  file: IconFile,
  fileText: IconFileText,
  attachment: IconPaperclip,

  // === Actions ===
  tool: IconTool,
  bolt: IconBolt,
  send: IconSend,
  trash: IconTrash,
  edit: IconEdit,
  plus: IconPlus,
  minus: IconMinus,
  refresh: IconRefresh,
  copy: IconCopy,
  download: IconDownload,
  upload: IconUpload,

  // === User & Security ===
  user: IconUser,
  users: IconUsers,
  userStar: IconUserStar,
  lock: IconLock,
  shield: IconShield,
  key: IconKey,

  // === Agent Specific ===
  heartbeat: IconHeartbeat,
  dna: IconDna,
  soul: IconDna,
  package: IconPackage,
  cloud: IconCloud,
  database: IconDatabase,

  // === Communication ===
  message: IconMessage,
  messages: IconMessages,
  inbox: IconInbox,
  listCheck: IconListCheck,
  plug: IconPlugConnected,

  // === UI Controls ===
  bulb: IconBulb,
  arrowRight: IconArrowRight,
  chevronDown: IconChevronDown,
  chevronRight: IconChevronRight,
  chevronLeft: IconChevronLeft,
  externalLink: IconExternalLink,
  search: IconSearch,
  settings: IconSettings,
  logout: IconLogout,
  menu: IconMenu,
  filter: IconFilter,

  // === Status Indicators ===
  circleCheck: IconCircleCheck,
  circleX: IconCircleX,
  circleDot: IconCircleDot,
  spinner: IconLoader2,

  // === Features ===
  target: IconTarget,
  sparkles: IconSparkles,
  star: IconStar,
  pin: IconPin,
  pinned: IconPinned,
  unlink: IconUnlink,
} as const;

// Type for icon names
export type IconName = keyof typeof Icons;

// Props interface
export interface IconProps {
  name?: IconName;
  size?: number | keyof typeof IconSize;
  stroke?: number | keyof typeof IconStroke;
  color?: string;
  className?: string;
  style?: React.CSSProperties;
  'aria-hidden'?: boolean;
  'aria-label'?: string;
}

/**
 * Icon component for consistent iconography across the app
 *
 * Usage:
 *   <Icon name="robot" size="md" />
 *   <Icon name="brain" size={20} stroke="light" />
 */
export function Icon({
  name,
  size = 'md',
  stroke = 'regular',
  color,
  className,
  style,
  'aria-hidden': ariaHidden = true,
  'aria-label': ariaLabel,
}: IconProps) {
  const IconComponent = name ? Icons[name] : IconCircleDot;
  const sizeValue = typeof size === 'string' ? IconSize[size] : size;
  const strokeValue = typeof stroke === 'string' ? IconStroke[stroke] : stroke;

  return (
    <IconComponent
      size={sizeValue}
      stroke={strokeValue}
      color={color}
      className={className}
      style={style}
      aria-hidden={ariaHidden}
      aria-label={ariaLabel}
    />
  );
}

// Pre-configured icon components for common use cases
export const StatusIcon = {
  running: () => <IconCircleCheck size={IconSize.sm} color="var(--status-running)" />,
  idle: () => <IconCircleDot size={IconSize.sm} color="var(--status-idle)" />,
  stopped: () => <IconCircleDot size={IconSize.sm} color="var(--status-stopped)" />,
  error: () => <IconCircleX size={IconSize.sm} color="var(--status-error)" />,
  creating: () => <IconLoader2 size={IconSize.sm} color="var(--warning)" className="animate-spin" />,
};

// Export all icons for direct import
export {
  // Navigation & Branding
  IconRobot,
  IconBrain,
  IconBuildingArch,
  IconBuilding,
  IconWorld,

  // Status & Feedback
  IconAlertCircle,
  IconAlertTriangle,
  IconCheck,
  IconX,
  IconInfoCircle,

  // Time & Date
  IconSun,
  IconSunHigh,
  IconMoon,
  IconCalendar,
  IconClock,
  IconHourglass,

  // Data & Content
  IconChartBar,
  IconChartLine,
  IconFolder,
  IconFile,
  IconFileText,
  IconPaperclip,

  // Actions
  IconTool,
  IconBolt,
  IconSend,
  IconTrash,
  IconEdit,
  IconPlus,
  IconMinus,
  IconRefresh,
  IconCopy,
  IconDownload,
  IconUpload,

  // User & Security
  IconUser,
  IconUsers,
  IconUserStar,
  IconLock,
  IconShield,
  IconKey,

  // Agent Specific
  IconHeartbeat,
  IconDna,
  IconPackage,
  IconCloud,
  IconDatabase,

  // Communication
  IconMessage,
  IconMessages,
  IconInbox,
  IconListCheck,
  IconPlugConnected,

  // UI Controls
  IconBulb,
  IconArrowRight,
  IconChevronDown,
  IconChevronRight,
  IconChevronLeft,
  IconExternalLink,
  IconSearch,
  IconSettings,
  IconLogout,
  IconMenu,
  IconFilter,

  // Status Indicators
  IconCircleCheck,
  IconCircleX,
  IconCircleDot,
  IconLoader2,

  // Features
  IconTarget,
  IconSparkles,
  IconStar,
  IconPin,
  IconPinned,
  IconUnlink,
};
