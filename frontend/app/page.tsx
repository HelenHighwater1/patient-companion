"use client";

import { useCallback, useEffect, useState } from "react";
import { AboutModal } from "@/components/AboutModal";
import { DisclaimerGate } from "@/components/DisclaimerGate";
import { DocumentPanel } from "@/components/DocumentPanel";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { PreviewModal } from "@/components/PreviewModal";
import { Chat, type ShowEvidenceOptions } from "@/components/chat/Chat";
import { EvidencePanel, type EvidenceFocus } from "@/components/evidence/EvidencePanel";
import { fetchCorpus, listDocuments } from "@/lib/api";
import type { CorpusSummary, Evidence, SampleDocument } from "@/lib/types";
import { useDialogFocus } from "@/lib/useDialogFocus";
import { useMediaQuery } from "@/lib/useMediaQuery";

export default function Home() {
  const [acknowledged, setAcknowledged] = useState(false);
  const [documents, setDocuments] = useState<SampleDocument[]>([]);
  const [docsStatus, setDocsStatus] = useState<"loading" | "ready" | "error">("loading");
  const [documentToLoad, setDocumentToLoad] = useState<SampleDocument | null>(null);
  const [previewDoc, setPreviewDoc] = useState<SampleDocument | null>(null);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [corpus, setCorpus] = useState<CorpusSummary | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [focus, setFocus] = useState<EvidenceFocus | null>(null);
  const [hoveredSourceKey, setHoveredSourceKey] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const wide = useMediaQuery("(min-width: 1280px)");
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);
  const drawerRef = useDialogFocus<HTMLDivElement>(drawerOpen && !wide, closeDrawer);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const deadline = Date.now() + 90_000;
    const attempt = async () => {
      try {
        const docs = await listDocuments();
        if (cancelled) return;
        setDocuments(docs);
        setDocsStatus("ready");
        fetchCorpus().then((c) => !cancelled && setCorpus(c));
      } catch {
        if (cancelled) return;
        if (Date.now() < deadline) timer = setTimeout(attempt, 4000);
        else setDocsStatus("error");
      }
    };
    void attempt();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    if (wide) setDrawerOpen(false);
  }, [wide]);

  const handleLoad = useCallback((doc: SampleDocument) => setDocumentToLoad(doc), []);
  const handleLoaded = useCallback(() => setDocumentToLoad(null), []);
  const handleLoadFromPreview = useCallback((doc: SampleDocument) => {
    setPreviewDoc(null);
    setDocumentToLoad(doc);
  }, []);

  const handleEvidence = useCallback(
    (e: Evidence, opts?: ShowEvidenceOptions) => {
      if (opts?.onlyIfActive) {
        setEvidence((prev) => (prev?.messageId === e.messageId ? e : prev));
        return;
      }
      setEvidence(e);
      setHoveredSourceKey(null);
      setFocus((f) => (opts?.marker ? { marker: opts.marker, tick: (f?.tick ?? 0) + 1 } : null));
      if (opts?.reveal && !wide) setDrawerOpen(true);
    },
    [wide],
  );

  const panel = (onClose?: () => void) => (
    <EvidencePanel
      corpus={corpus}
      evidence={evidence}
      focus={focus}
      hoveredKey={hoveredSourceKey}
      onHoverSource={setHoveredSourceKey}
      onClear={() => {
        setEvidence(null);
        setFocus(null);
      }}
      onClose={onClose}
    />
  );

  return (
    <>
      {!acknowledged && <DisclaimerGate onAcknowledge={() => setAcknowledged(true)} />}
      <div className="flex h-screen flex-col">
        <Header onOpenAbout={() => setAboutOpen(true)} onOpenEvidence={() => setDrawerOpen(true)} />
        <Hero />
        <div className="mx-auto flex w-full max-w-[1440px] flex-1 gap-5 overflow-hidden px-4 pb-5 pt-4">
          <div className="hidden w-72 shrink-0 md:block xl:w-64">
            <DocumentPanel
              documents={documents}
              status={docsStatus}
              activeFilename={documentToLoad?.filename ?? null}
              onLoad={handleLoad}
              onPreview={setPreviewDoc}
            />
          </div>
          <main className="min-w-0 flex-1 overflow-hidden rounded-3xl bg-paper shadow-float">
            <Chat
              documentToLoad={documentToLoad}
              onDocumentLoaded={handleLoaded}
              wide={wide}
              activeEvidenceId={evidence?.messageId ?? null}
              hoveredSourceKey={hoveredSourceKey}
              onEvidence={handleEvidence}
            />
          </main>
          <div className="hidden w-[380px] shrink-0 xl:block">{panel()}</div>
        </div>
      </div>
      {drawerOpen && !wide && (
        <div
          className="fixed inset-0 z-40 flex justify-end bg-warm-900/40 p-3 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Evidence"
          onClick={closeDrawer}
        >
          <div
            ref={drawerRef}
            className="h-full w-full max-w-[400px]"
            onClick={(e) => e.stopPropagation()}
          >
            {panel(closeDrawer)}
          </div>
        </div>
      )}
      {previewDoc && (
        <PreviewModal doc={previewDoc} onClose={() => setPreviewDoc(null)} onLoad={handleLoadFromPreview} />
      )}
      {aboutOpen && <AboutModal onClose={() => setAboutOpen(false)} />}
    </>
  );
}
