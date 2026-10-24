import { AlertCircle } from "lucide-react";
import type { ReactNode } from "react";

type ErrorStateProps = {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
};

export function ErrorState({ title, description, action }: ErrorStateProps) {
  return (
    <div role="alert" className="rounded border border-danger/30 bg-danger/5 p-6 text-center">
      <AlertCircle aria-hidden="true" className="mx-auto h-6 w-6 text-danger" />
      <p className="mt-3 text-lg font-semibold text-text">{title}</p>
      {description ? <p className="mt-2 text-sm text-muted">{description}</p> : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}
