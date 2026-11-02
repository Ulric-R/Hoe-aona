import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Icon } from './shared/icon';

interface NavItem { path: string; label: string; icon: string; }

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon],
  templateUrl: './app.html',
  styleUrl: './app.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  protected readonly nav: NavItem[] = [
    { path: '/analyser', label: 'Analyser', icon: 'add' },
    { path: '/resultat', label: 'Résultat', icon: 'gauge' },
    { path: '/historique', label: 'Historique', icon: 'history' },
    { path: '/parametres', label: 'Paramètres', icon: 'settings' },
  ];
}
