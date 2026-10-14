import { useEffect, useState } from 'react';
import type { HarveyApi } from '../services/api';
import type { Notify } from '../contracts';

interface Profile {
  language: 'pt-BR' | 'en';
  allowed_languages: ('pt-BR' | 'en')[];
  tone: string;
  detail: string;
  interaction: string;
  guidance: string;
  version: number;
  scope: string;
}

const defaultProfile: Profile = {
  language: 'pt-BR',
  allowed_languages: ['pt-BR', 'en'],
  tone: 'natural',
  detail: 'balanced',
  interaction: '',
  guidance: '',
  version: 1,
  scope: 'global',
};

function normalizeProfile(data: Partial<Profile> | null | undefined): Profile {
  return {
    ...defaultProfile,
    ...(data || {}),
    language: data?.language === 'en' ? 'en' : 'pt-BR',
    allowed_languages: Array.isArray(data?.allowed_languages) ? data.allowed_languages : ['pt-BR', 'en'],
    tone: data?.tone || 'natural',
    detail: data?.detail || 'balanced',
    interaction: data?.interaction || '',
    guidance: data?.guidance || '',
    version: typeof data?.version === 'number' ? data.version : 1,
    scope: data?.scope || 'global',
  };
}

export async function responseData(response: Response) {
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Dados inválidos. Confira os campos.');
  return data;
}

export default function ProfileEditor({ api, onNotice }: { api: HarveyApi; onNotice: Notify }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    void api
      .profile()
      .then(responseData)
      .then((data) => {
        if (alive) setProfile(normalizeProfile(data));
      })
      .catch(() => {
        if (alive) {
          setProfile(defaultProfile);
        }
      });
    return () => {
      alive = false;
    };
  }, [api]);

  const load = async () => {
    try {
      const data = await responseData(await api.profile());
      setProfile(normalizeProfile(data));
      setError('');
    } catch {
      setProfile(defaultProfile);
      setError('Não foi possível carregar o perfil.');
    }
  };

  if (!profile) return <div role="status">{error || 'Carregando perfil…'}{error && <button className="text-button" onClick={() => void load()}>Tentar novamente</button>}</div>;

  const change = (key: keyof Profile, value: unknown) => setProfile({ ...profile, [key]: value });

  return (
    <form
      className="extension-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError('');
        const { version, scope, ...body } = profile;
        try {
          const res = await responseData(await api.saveProfile(body, version));
          setProfile(normalizeProfile(res));
          onNotice('Perfil salvo. Aplicação na próxima conversa.', 'success');
        } catch (err) {
          setError((err as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <p className="settings-help">Suas preferências valem em todos os dispositivos e são aplicadas na próxima conversa.</p>
      <label>
        Idioma principal
        <select aria-label="Idioma principal" value={profile.language || 'pt-BR'} onChange={(e) => change('language', e.target.value)}>
          <option value="pt-BR">Português do Brasil</option>
          <option value="en">English</option>
        </select>
      </label>
      <fieldset>
        <legend>Idiomas permitidos por padrão</legend>
        {(['pt-BR', 'en'] as const).map((language) => (
          <label className="checkbox-field" key={language}>
            <input
              type="checkbox"
              checked={Boolean(profile.allowed_languages?.includes(language))}
              onChange={(e) => {
                const current = profile.allowed_languages || ['pt-BR', 'en'];
                change('allowed_languages', e.target.checked ? [...current, language] : current.filter((l) => l !== language));
              }}
            />
            {language === 'pt-BR' ? 'Português' : 'English'}
          </label>
        ))}
      </fieldset>
      <label>
        Tom
        <select aria-label="Tom" value={profile.tone || 'natural'} onChange={(e) => change('tone', e.target.value)}>
          <option value="natural">Natural</option>
          <option value="formal">Formal</option>
          <option value="casual">Informal</option>
        </select>
      </label>
      <label>
        Detalhamento
        <select aria-label="Detalhamento" value={profile.detail || 'balanced'} onChange={(e) => change('detail', e.target.value)}>
          <option value="brief">Breve</option>
          <option value="balanced">Equilibrado</option>
          <option value="detailed">Detalhado</option>
        </select>
      </label>
      <label>
        Preferências de interação
        <textarea maxLength={2000} value={profile.interaction || ''} onChange={(e) => change('interaction', e.target.value)} />
      </label>
      <label>
        Orientações pessoais
        <textarea maxLength={4000} value={profile.guidance || ''} onChange={(e) => change('guidance', e.target.value)} />
      </label>
      <p className="settings-help">Seu pedido explícito prevalece sobre preferências padrão, dentro das permissões. Habilidades e conteúdo externo não ampliam acesso. Histórico não vira memória automaticamente.</p>
      {error && (
        <div className="error-banner" role="alert">
          {error} <button type="button" className="text-button" onClick={() => void load()}>Recarregar perfil</button>
        </div>
      )}
      <button className="primary-button" disabled={busy} type="submit">
        {busy ? 'Salvando…' : 'Salvar perfil'}
      </button>
    </form>
  );
}
