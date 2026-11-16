import { ChatPlaceholder } from "@/features/auth/components/ChatPlaceholder";
import { RequireAuth } from "@/features/auth/components/RequireAuth";

export default function ChatPage() {
  return (
    <RequireAuth>
      <ChatPlaceholder />
    </RequireAuth>
  );
}
