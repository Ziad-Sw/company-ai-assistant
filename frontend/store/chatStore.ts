import { create } from "zustand";

type ChatState = {
  /** المحادثة المفتوحة دلوقتي في الواجهة — null = محادثة جديدة لسه ماتحفظتش. */
  activeConversationId: string | null;
  /** الموديل المختار من الـdropdown — محادثة بس، مبيتخزنش في localStorage. */
  selectedModel: string | null;
  /**
   * عدّاد بيتزوّد لما محادثة جديدة تتضاف (أول رسالة) — الـsidebar بيعمل
   * refetch لما الرقم يتغيّر بدل ما يعمل polling.
   */
  conversationsVersion: number;
  setActiveConversation: (conversationId: string | null) => void;
  setSelectedModel: (model: string | null) => void;
  bumpConversations: () => void;
};

/** حالة الشات للعرض بس — التفويض والحفظ على الـbackend، زي الـauthStore. */
export const useChatStore = create<ChatState>()((set) => ({
  activeConversationId: null,
  selectedModel: null,
  conversationsVersion: 0,
  setActiveConversation: (conversationId) => set({ activeConversationId: conversationId }),
  setSelectedModel: (model) => set({ selectedModel: model }),
  bumpConversations: () => set((state) => ({ conversationsVersion: state.conversationsVersion + 1 })),
}));
