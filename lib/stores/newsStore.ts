import { create } from 'zustand';
import { NewsItem } from '../types';

interface NewsState {
  news: NewsItem[];
  loading: boolean;
  lastUpdate: number;

  setNews: (news: NewsItem[]) => void;
  addNews: (item: NewsItem) => void;
  updateNewsAnalysis: (id: string, analysis: NewsItem['aiAnalysis']) => void;
  setLoading: (loading: boolean) => void;
}

export const useNewsStore = create<NewsState>((set) => ({
  news: [],
  loading: false,
  lastUpdate: 0,

  setNews: (news) => set({ news, lastUpdate: Date.now() }),

  addNews: (item) => set((state) => ({
    news: [item, ...state.news].slice(0, 50),
  })),

  updateNewsAnalysis: (id, analysis) => set((state) => ({
    news: state.news.map(item =>
      item.id === id ? { ...item, aiAnalysis: analysis } : item
    ),
  })),

  setLoading: (loading) => set({ loading }),
}));
