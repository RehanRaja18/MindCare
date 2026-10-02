// ============================================================
// MindCare — Form field building blocks for the sign-up forms
// Label + control + error/hint, with consistent styling and a11y.
// ============================================================

import React, { useId } from 'react';
import { cn } from '../../utils/cn';
import type { Option } from '../../utils/locale';

const controlClass = (error?: string) =>
  cn(
    'w-full px-4 py-3 text-base sm:text-sm border rounded-xl focus:outline-none focus:ring-2 bg-white',
    error ? 'border-red-300 focus:ring-red-500' : 'border-gray-200 focus:ring-gray-900'
  );

interface FieldProps {
  label: string;
  error?: string;
  hint?: string;
  required?: boolean;
  className?: string;
  children: (props: { id: string; 'aria-invalid': boolean; 'aria-describedby'?: string; className: string }) => React.ReactNode;
}

export const Field: React.FC<FieldProps> = ({ label, error, hint, required, className, children }) => {
  const id = useId();
  const noteId = `${id}-note`;
  return (
    <div className={className}>
      <label htmlFor={id} className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
        {label}
        {required && ' *'}
      </label>
      {children({
        id,
        'aria-invalid': !!error,
        'aria-describedby': error || hint ? noteId : undefined,
        className: controlClass(error),
      })}
      {error ? (
        <p id={noteId} role="alert" className="text-xs text-red-600 mt-1.5">
          {error}
        </p>
      ) : hint ? (
        <p id={noteId} className="text-xs text-gray-500 mt-1.5">
          {hint}
        </p>
      ) : null}
    </div>
  );
};

type InputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'value'> & {
  label: string;
  value: string;
  onValue: (v: string) => void;
  error?: string;
  hint?: string;
  fieldClassName?: string;
};

export const TextField: React.FC<InputProps> = ({ label, value, onValue, error, hint, required, fieldClassName, ...rest }) => (
  <Field label={label} error={error} hint={hint} required={required} className={fieldClassName}>
    {(p) => <input {...rest} {...p} value={value} onChange={(e) => onValue(e.target.value)} />}
  </Field>
);

export const TextAreaField: React.FC<
  Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, 'onChange' | 'value'> & {
    label: string;
    value: string;
    onValue: (v: string) => void;
    error?: string;
    hint?: string;
    fieldClassName?: string;
  }
> = ({ label, value, onValue, error, hint, required, fieldClassName, ...rest }) => (
  <Field label={label} error={error} hint={hint} required={required} className={fieldClassName}>
    {(p) => <textarea {...rest} {...p} value={value} onChange={(e) => onValue(e.target.value)} className={cn(p.className, 'resize-none')} />}
  </Field>
);

export const SelectField: React.FC<{
  label: string;
  value: string;
  onValue: (v: string) => void;
  options: Option[];
  placeholder?: string;
  error?: string;
  hint?: string;
  required?: boolean;
  fieldClassName?: string;
}> = ({ label, value, onValue, options, placeholder, error, hint, required, fieldClassName }) => (
  <Field label={label} error={error} hint={hint} required={required} className={fieldClassName}>
    {(p) => (
      <select {...p} value={value} onChange={(e) => onValue(e.target.value)}>
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    )}
  </Field>
);

/** Pill-style multi-select (languages, specializations). */
export const ChipGroup: React.FC<{
  label: string;
  options: Option[];
  selected: string[];
  onToggle: (value: string) => void;
  error?: string;
  hint?: string;
  required?: boolean;
}> = ({ label, options, selected, onToggle, error, hint, required }) => (
  <fieldset>
    <legend className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-3">
      {label}
      {required && ' *'}
    </legend>
    <div className="flex flex-wrap gap-2">
      {options.map((o) => {
        const on = selected.includes(o.value);
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => onToggle(o.value)}
            className={cn(
              'px-4 py-2 rounded-full text-sm font-semibold border transition-colors',
              on ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-700 border-gray-200 hover:border-gray-400'
            )}
          >
            {o.label} {on && '✓'}
          </button>
        );
      })}
    </div>
    {error ? (
      <p role="alert" className="text-xs text-red-600 mt-2">
        {error}
      </p>
    ) : hint ? (
      <p className="text-xs text-gray-500 mt-2">{hint}</p>
    ) : null}
  </fieldset>
);

/** "I confirm I am 18 or older" — the backend requires is_adult_confirmed: true. */
export const AdultConfirm: React.FC<{ checked: boolean; onChange: (v: boolean) => void; error?: string }> = ({
  checked,
  onChange,
  error,
}) => (
  <div>
    <label className="flex items-start gap-3 bg-[#EFE9DF] rounded-xl px-4 py-4 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        aria-invalid={!!error}
        className="w-4 h-4 mt-0.5 rounded border-gray-300 accent-gray-900 shrink-0"
      />
      <span className="text-sm text-gray-700">I confirm that I am 18 years of age or older.</span>
    </label>
    {error && (
      <p role="alert" className="text-xs text-red-600 mt-1.5">
        {error}
      </p>
    )}
  </div>
);
