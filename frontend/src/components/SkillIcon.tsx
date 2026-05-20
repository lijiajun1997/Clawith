import React from 'react';
import {
    IconBrain, IconFileText, IconCalculator, IconSearch, IconCode,
    IconMessage, IconClipboard, IconRobot, IconChartBar, IconMail,
    IconPackages, IconTool, IconPencil, IconBooks, IconShield,
    IconBriefcase, IconUsers, IconDatabase, IconSettings, IconRocket,
    IconGlobe, IconMicrophone, IconCamera, IconMusic, IconPalette,
    IconCalendar, IconClock, IconBell, IconStar, IconHeart,
    IconBookmark, IconFlag, IconTarget, IconCompass, IconBulb,
    IconWriting, IconReportAnalytics, IconFileCheck, IconScale,
    IconPresentationAnalytics, IconCoins, IconReceipt,
    IconFileTypePdf, IconPresentation, IconTable, IconFileSpreadsheet,
    IconChecklist, IconCertificate, IconGavel, IconBuildingBank,
    IconGraph, IconTrendingUp, IconClipboardCheck, IconFileAnalytics,
    IconNotebook, IconBook, IconSchool, IconWorld, IconLanguage,
    IconTransferIn, IconPlayerPlay, IconSparkles, IconWand,
} from '@tabler/icons-react';

// Tabler 图标映射表
const TABLER_ICON_MAP: Record<string, React.ComponentType<any>> = {
    IconBrain, IconFileText, IconCalculator, IconSearch, IconCode,
    IconMessage, IconClipboard, IconRobot, IconChartBar, IconMail,
    IconPackages, IconTool, IconPencil, IconBooks, IconShield,
    IconBriefcase, IconUsers, IconDatabase, IconSettings, IconRocket,
    IconGlobe, IconMicrophone, IconCamera, IconMusic, IconPalette,
    IconCalendar, IconClock, IconBell, IconStar, IconHeart,
    IconBookmark, IconFlag, IconTarget, IconCompass, IconBulb,
    IconWriting, IconReportAnalytics, IconFileCheck, IconScale,
    IconPresentationAnalytics, IconCoins, IconReceipt,
    IconFileTypePdf, IconPresentation, IconTable, IconFileSpreadsheet,
    IconChecklist, IconCertificate, IconGavel, IconBuildingBank,
    IconGraph, IconTrendingUp, IconClipboardCheck, IconFileAnalytics,
    IconNotebook, IconBook, IconSchool, IconWorld, IconLanguage,
    IconTransferIn, IconPlayerPlay, IconSparkles, IconWand,
};

// 所有可选图标名列表
export const AVAILABLE_TABLER_ICONS = Object.keys(TABLER_ICON_MAP);

// 默认图标
const DEFAULT_ICON = 'IconPackages';

interface SkillIconProps {
    icon: string;
    size?: number;
    style?: React.CSSProperties;
    className?: string;
}

// Check if a string is a Tabler icon name (starts with "Icon")
function isTablerIconName(val: string): val is keyof typeof TABLER_ICON_MAP {
    return val.startsWith('Icon') && val in TABLER_ICON_MAP;
}

const SkillIcon: React.FC<SkillIconProps> = ({ icon, size = 28, style, className }) => {
    const iconStr = (icon && icon !== '--') ? icon : '';
    const tablerIcon = isTablerIconName(iconStr) ? TABLER_ICON_MAP[iconStr] : null;

    return (
        <div
            style={{
                width: size, height: size,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                borderRadius: `${Math.round(size * 0.25)}px`,
                background: 'var(--accent-subtle)',
                color: 'var(--accent-primary)',
                flexShrink: 0,
                ...style,
            }}
            className={className}
        >
            {tablerIcon
                ? React.createElement(tablerIcon, { size: Math.round(size * 0.6), stroke: 1.5 })
                : <span style={{ fontSize: Math.round(size * 0.55), lineHeight: 1 }}>{iconStr || '?'}</span>
            }
        </div>
    );
};

export default SkillIcon;
export { TABLER_ICON_MAP };
