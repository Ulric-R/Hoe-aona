import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { AnalysisOut, AnalysisPage, Article, Health, Preferences } from './models';

@Injectable({ providedIn: 'root' })
export class Api {
  private readonly http = inject(HttpClient);
  private readonly base = '/api';

  createAnalysis(payload: { text: string; urls: string[]; files: File[] }) {
    const form = new FormData();
    form.append('text', payload.text);
    form.append('urls', JSON.stringify(payload.urls));
    payload.files.forEach((f) => form.append('files', f, f.name));
    return this.http.post<AnalysisOut>(`${this.base}/analyses`, form);
  }

  getAnalysis(id: string) {
    return this.http.get<AnalysisOut>(`${this.base}/analyses/${id}`);
  }

  listAnalyses(opts: { q?: string; verdict?: string | null; limit?: number; offset?: number } = {}) {
    let params = new HttpParams().set('limit', opts.limit ?? 20).set('offset', opts.offset ?? 0);
    if (opts.q) params = params.set('q', opts.q);
    if (opts.verdict) params = params.set('verdict', opts.verdict);
    return this.http.get<AnalysisPage>(`${this.base}/analyses`, { params });
  }

  deleteAnalysis(id: string) {
    return this.http.delete<void>(`${this.base}/analyses/${id}`);
  }

  regenerateArticle(id: string) {
    return this.http.post<Article>(`${this.base}/analyses/${id}/article`, {});
  }

  articleUrl(id: string, format: 'md' | 'html') {
    return `${this.base}/analyses/${id}/article.${format}`;
  }

  getSettings() {
    return this.http.get<Preferences>(`${this.base}/settings`);
  }

  saveSettings(prefs: Preferences) {
    return this.http.put<Preferences>(`${this.base}/settings`, prefs);
  }

  health() {
    return this.http.get<Health>(`${this.base}/health`);
  }
}

/** Message d'erreur lisible à partir d'une réponse FastAPI. */
export function errorMessage(err: unknown): string {
  const e = err as { status?: number; error?: { detail?: unknown } };
  const detail = e?.error?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) return String((detail[0] as { msg?: string }).msg ?? 'Requête invalide');
  if (e?.status === 0) return 'Serveur injoignable : vérifiez que le backend est démarré.';
  return 'Une erreur est survenue. Réessayez dans un instant.';
}
