"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type MouseEvent } from "react";

import {
  emptyFormValues,
  shouldShowEveningWarning,
  validateConsent,
  validateDob,
  validateEmail,
  validateHealthConcern,
  validateInsuranceProvider,
  validateMemberId,
  validateNameField,
  validatePatientId,
  validatePhone,
  validatePreferredDate,
  validateRequiredSelect,
  validateService,
  type EnquiryFormValues,
  type FieldErrors,
} from "@/lib/enquiry-validation";
import { useLanguage } from "@/lib/i18n/language-context";

type FieldName = keyof EnquiryFormValues;

const BLUR_FIELDS: FieldName[] = [
  "first_name",
  "last_name",
  "email",
  "phone",
  "insurance_provider",
  "insurance_member_id",
  "patient_id",
];

const SELECT_FIELDS: FieldName[] = ["preferred_language", "preferred_clinic", "preferred_time"];

const setFieldError = (errors: FieldErrors, field: FieldName, message: string | null): FieldErrors => {
  const next = { ...errors };
  if (message) next[field] = message;
  else delete next[field];
  return next;
};

export const useEnquiryForm = () => {
  const { lang, t } = useLanguage();
  const [values, setValues] = useState<EnquiryFormValues>(emptyFormValues);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [modalOpen, setModalOpen] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const okBtnRef = useRef<HTMLButtonElement>(null);
  const firstNameRef = useRef<HTMLInputElement>(null);

  const showPatientId = values.new_patient === "No";
  const showInsuranceFields = values.has_insurance === "Yes";
  const showEveningWarning = shouldShowEveningWarning(values.preferred_clinic, values.preferred_time);
  const concernLength = values.health_concern.trim().length;

  const dateLocale = useMemo(
    () => ({
      lang: lang === "es" ? "es-ES" : "en-US",
      placeholder: lang === "es" ? "aaaa-mm-dd" : "yyyy-mm-dd",
      title: lang === "es" ? "Selecciona una fecha en el calendario" : "Select a date from the calendar",
    }),
    [lang]
  );

  const runValidator = useCallback(
    (field: FieldName, v: EnquiryFormValues): string | null => {
      switch (field) {
        case "first_name":
        case "last_name":
          return validateNameField(lang, v[field], field);
        case "date_of_birth":
          return validateDob(lang, v.date_of_birth);
        case "email":
          return validateEmail(lang, v.email);
        case "phone":
          return validatePhone(lang, v.phone);
        case "preferred_language":
          return validateRequiredSelect(lang, v.preferred_language, "preferred_language");
        case "preferred_clinic":
          return validateRequiredSelect(lang, v.preferred_clinic, "preferred_clinic");
        case "preferred_date":
          return validatePreferredDate(lang, v.preferred_date);
        case "preferred_time":
          return validateRequiredSelect(lang, v.preferred_time, "preferred_time");
        case "service_type":
          return validateService(lang, v.service_type, v.date_of_birth);
        case "new_patient":
          return validateRequiredSelect(lang, v.new_patient, "new_patient");
        case "has_insurance":
          return validateRequiredSelect(lang, v.has_insurance, "has_insurance");
        case "insurance_provider":
          return validateInsuranceProvider(lang, v.has_insurance, v.insurance_provider);
        case "insurance_member_id":
          return validateMemberId(lang, v.has_insurance, v.insurance_member_id);
        case "patient_id":
          return validatePatientId(lang, v.new_patient, v.patient_id);
        case "health_concern":
          return validateHealthConcern(lang, v.health_concern, (key) => t(key));
        case "contact_consent":
          return validateConsent(lang, v.contact_consent);
        default:
          return null;
      }
    },
    [lang, t]
  );

  const validateOne = useCallback(
    (field: FieldName, nextValues?: EnquiryFormValues) => {
      const v = nextValues ?? values;
      const message = runValidator(field, v);
      setErrors((prev) => setFieldError(prev, field, message));
      return message === null;
    },
    [runValidator, values]
  );

  const validateAll = useCallback(() => {
    const fields = Object.keys(emptyFormValues()) as FieldName[];
    let ok = true;
    const nextErrors: FieldErrors = {};
    fields.forEach((field) => {
      const message = runValidator(field, values);
      if (message) {
        nextErrors[field] = message;
        ok = false;
      }
    });
    setErrors(nextErrors);
    return ok;
  }, [runValidator, values]);

  const onBlur = useCallback(
    (field: FieldName) => validateOne(field),
    [validateOne]
  );

  const onChange = useCallback(
    (field: FieldName, value: string | boolean) => {
      const next = { ...values, [field]: value } as EnquiryFormValues;
      setValues(next);
      if (BLUR_FIELDS.includes(field) || field === "health_concern") validateOne(field, next);
      if (field === "date_of_birth") {
        validateOne("date_of_birth", next);
        validateOne("service_type", next);
      }
      if (field === "new_patient") {
        validateOne("new_patient", next);
        validateOne("patient_id", next);
      }
      if (field === "has_insurance") {
        validateOne("has_insurance", next);
        validateOne("insurance_provider", next);
        validateOne("insurance_member_id", next);
      }
      if (SELECT_FIELDS.includes(field) || field === "preferred_date" || field === "service_type") {
        validateOne(field, next);
      }
      if (field === "contact_consent") validateOne("contact_consent", next);
    },
    [validateOne, values]
  );

  const resetForm = useCallback(() => {
    setValues(emptyFormValues());
    setErrors({});
    setModalOpen(false);
    document.body.classList.remove("overflow-hidden");
  }, []);

  const openModal = useCallback(() => {
    setModalOpen(true);
    document.body.classList.add("overflow-hidden");
    requestAnimationFrame(() => okBtnRef.current?.focus());
  }, []);

  const closeModal = useCallback(() => {
    setModalOpen(false);
    document.body.classList.remove("overflow-hidden");
    firstNameRef.current?.focus();
  }, []);

  const onSubmit = useCallback(
    (event: FormEvent) => {
      event.preventDefault();
      if (!validateAll()) {
        setModalOpen(false);
        document.body.classList.remove("overflow-hidden");
        return;
      }
      setValues(emptyFormValues());
      setErrors({});
      openModal();
    },
    [openModal, validateAll]
  );

  const onClear = useCallback(() => resetForm(), [resetForm]);

  const onModalBackdropClick = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if (event.target === modalRef.current) closeModal();
    },
    [closeModal]
  );

  useEffect(() => {
    if (!modalOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeModal();
        return;
      }
      if (event.key !== "Tab" || !modalRef.current) return;
      const focusable = Array.from(
        modalRef.current.querySelectorAll<HTMLElement>(
          "button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])"
        )
      ).filter((el) => !el.hasAttribute("disabled") && el.getAttribute("aria-hidden") !== "true");
      if (focusable.length === 0) {
        event.preventDefault();
        modalRef.current.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [closeModal, modalOpen]);

  const displayErrors = useMemo(() => {
    const next: FieldErrors = {};
    (Object.keys(errors) as FieldName[]).forEach((field) => {
      const message = runValidator(field, values);
      if (message) next[field] = message;
    });
    return next;
  }, [errors, runValidator, values]);

  return {
    values,
    errors: displayErrors,
    modalOpen,
    showPatientId,
    showInsuranceFields,
    showEveningWarning,
    concernLength,
    dateLocale,
    modalRef,
    okBtnRef,
    firstNameRef,
    onBlur,
    onChange,
    onSubmit,
    onClear,
    closeModal,
    onModalBackdropClick,
  };
};

export type EnquiryFormApi = ReturnType<typeof useEnquiryForm>;
