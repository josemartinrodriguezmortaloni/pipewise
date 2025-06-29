import ChatPageClient from "@/components/chat/page";

// Disable static generation for this page
export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function ChatPage() {
  return <ChatPageClient />;
}
