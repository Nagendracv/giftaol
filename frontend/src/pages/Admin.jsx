import { useLang } from "../lib/i18n";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { ContentEditor } from "../components/admin/ContentEditor";
import { ConfigPanel } from "../components/admin/ConfigPanel";
import { HackMonitor } from "../components/admin/HackMonitor";

export default function Admin() {
  const { t } = useLang();
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-10" data-testid="admin-page">
      <h1 className="font-serif text-4xl sm:text-5xl text-stone-900">{t("admin.title")}</h1>
      <Tabs defaultValue="content" className="mt-6">
        <TabsList className="bg-stone-100 p-1 rounded-xl h-auto flex-wrap justify-start">
          <TabsTrigger value="content" data-testid="admin-tab-content-editor" className="rounded-lg px-4 py-2">{t("admin.tab_content")}</TabsTrigger>
          <TabsTrigger value="config" data-testid="admin-tab-config" className="rounded-lg px-4 py-2">{t("admin.tab_config")}</TabsTrigger>
          <TabsTrigger value="monitor" data-testid="admin-tab-hack-monitor" className="rounded-lg px-4 py-2">{t("admin.tab_monitor")}</TabsTrigger>
        </TabsList>
        <TabsContent value="content" className="pt-4"><ContentEditor /></TabsContent>
        <TabsContent value="config" className="pt-4"><ConfigPanel /></TabsContent>
        <TabsContent value="monitor" className="pt-4"><HackMonitor /></TabsContent>
      </Tabs>
    </div>
  );
}
