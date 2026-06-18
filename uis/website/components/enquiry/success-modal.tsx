"use client";

import type { RefObject } from "react";

import { useLanguage } from "@/lib/i18n/language-context";

type SuccessModalProps = {
  open: boolean;
  modalRef: RefObject<HTMLDivElement | null>;
  okBtnRef: RefObject<HTMLButtonElement | null>;
  onClose: () => void;
  onBackdropClick: (event: React.MouseEvent<HTMLDivElement>) => void;
};

export const SuccessModal = ({
  open,
  modalRef,
  okBtnRef,
  onClose,
  onBackdropClick,
}: SuccessModalProps) => {
  const { t } = useLanguage();
  if (!open) return null;

  return (
    <div
      ref={modalRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="successModalTitle"
      aria-describedby="successModalBody"
      tabIndex={-1}
      onClick={onBackdropClick}
    >
      <div className="w-full max-w-xl rounded-xl border border-emerald-300 bg-white p-6 text-emerald-900 shadow-2xl">
        <h2 id="successModalTitle" className="text-lg font-bold">
          {t("successTitle")}
        </h2>
        <div id="successModalBody">
          <p className="mt-2">{t("successBody1")}</p>
          <p className="mt-2">{t("successBody2")}</p>
          <p className="mt-2">{t("successBody3")}</p>
        </div>
        <div className="mt-5 flex justify-end">
          <button
            ref={okBtnRef}
            type="button"
            onClick={onClose}
            className="rounded-md bg-sky-700 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-sky-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
          >
            {t("successOkBtn")}
          </button>
        </div>
      </div>
    </div>
  );
};
