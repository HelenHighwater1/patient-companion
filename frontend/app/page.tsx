"use client";

import { useCallback, useEffect, useState } from "react";
import { AboutModal } from "@/components/AboutModal";
import { DisclaimerGate } from "@/components/DisclaimerGate";
import { DocumentPanel } from "@/components/DocumentPanel";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { PreviewModal } from "@/components/PreviewModal";
import { Chat } from "@/components/chat/Chat";
import { listDocuments } from "@/lib/api";
import type { SampleDocument } from "@/lib/types";

export default function Home() {
  const [acknowledged, setAcknowledged] = useState(false);
  const [documents, setDocuments] = useState<SampleDocument[]>([]);
  const [documentToLoad, setDocumentToLoad] = useState<SampleDocument | null>(null);
  const [previewDoc, setPreviewDoc] = useState<SampleDocument | null>(null);
  const [aboutOpen, setAboutOpen] = useState(false);

  useEffect(() => {
    listDocuments().then(setDocuments);
  }, []);

  const handleLoad = useCallback((doc: SampleDocument) => setDocumentToLoad(doc), []);
  const handleLoaded = useCallback(() => setDocumentToLoad(null), []);
  const handleLoadFromPreview = useCallback((doc: SampleDocument) => {
    setPreviewDoc(null);
    setDocumentToLoad(doc);
  }, []);

  return (
    <>
      {!acknowledged && <DisclaimerGate onAcknowledge={() => setAcknowledged(true)} />}
      <div className="flex h-screen flex-col">
        <Header onOpenAbout={() => setAboutOpen(true)} />
        <Hero />
        <div className="mx-auto flex w-full max-w-[1440px] flex-1 gap-5 overflow-hidden px-4 pb-5 pt-4">
          <div className="hidden w-72 shrink-0 md:block">
            <DocumentPanel
              documents={documents}
              activeFilename={documentToLoad?.filename ?? null}
              onLoad={handleLoad}
              onPreview={setPreviewDoc}
            />
          </div>
          <main className="min-w-0 flex-1 overflow-hidden rounded-3xl bg-paper shadow-float">
            <Chat documentToLoad={documentToLoad} onDocumentLoaded={handleLoaded} />
          </main>
        </div>
      </div>
      {previewDoc && (
        <PreviewModal doc={previewDoc} onClose={() => setPreviewDoc(null)} onLoad={handleLoadFromPreview} />
      )}
      {aboutOpen && <AboutModal onClose={() => setAboutOpen(false)} />}
    </>
  );
}
