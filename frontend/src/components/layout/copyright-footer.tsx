import { SidebarMenu, SidebarMenuItem } from '@/components/ui/sidebar';

export function CopyrightFooter() {
  const appName = import.meta.env.VITE_APP_NAME || 'Procesos Filament';
  const currentYear = new Date().getFullYear();

  return (
    <SidebarMenu>
      <SidebarMenuItem className="justify-center text-center py-2">
        <div className="text-xs text-muted-foreground">
          {appName} © {currentYear}
        </div>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}