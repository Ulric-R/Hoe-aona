import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'analyser' },
  { path: 'analyser', title: 'Analyser — Vérifia', loadComponent: () => import('./pages/analyze/analyze-page').then((m) => m.AnalyzePage) },
  { path: 'resultat', title: 'Résultat — Vérifia', loadComponent: () => import('./pages/result/result-page').then((m) => m.ResultPage) },
  { path: 'resultat/:id', title: 'Résultat — Vérifia', loadComponent: () => import('./pages/result/result-page').then((m) => m.ResultPage) },
  { path: 'historique', title: 'Historique — Vérifia', loadComponent: () => import('./pages/history/history-page').then((m) => m.HistoryPage) },
  { path: 'parametres', title: 'Paramètres — Vérifia', loadComponent: () => import('./pages/settings/settings-page').then((m) => m.SettingsPage) },
  { path: '**', redirectTo: 'analyser' },
];
