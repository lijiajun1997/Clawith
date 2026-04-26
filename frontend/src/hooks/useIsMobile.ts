import { useState, useEffect } from 'react';

const MOBILE_BREAKPOINT = 768;

export function useIsMobile() {
    const [isMobile, setIsMobile] = useState(() => window.innerWidth < MOBILE_BREAKPOINT);

    useEffect(() => {
        let timer: ReturnType<typeof setTimeout>;
        const handleResize = () => {
            clearTimeout(timer);
            timer = setTimeout(() => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT), 150);
        };
        window.addEventListener('resize', handleResize);
        return () => {
            clearTimeout(timer);
            window.removeEventListener('resize', handleResize);
        };
    }, []);

    return { isMobile };
}
