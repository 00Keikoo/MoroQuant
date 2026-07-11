import { LabShell } from '@/components/lab/LabShell';

export default function LabLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <LabShell>{children}</LabShell>;
}
