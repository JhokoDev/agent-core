/** Credencial efêmera do componente local; nunca contém chave do provedor. */
let channel:Promise<string>|null=null;
export async function desktopRequest(path:string,body?:unknown):Promise<any>{
  if(!channel)channel=fetch('/api/desktop/channel').then(async r=>{if(!r.ok)throw new Error('Componente local não vinculado.');return (await r.json()).token as string;}).catch(e=>{channel=null;throw e;});
  const token=await channel;
  const response=await fetch('/api/desktop/'+path,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok){if(response.status===403)channel=null;let data;try{data=await response.json();}catch{}throw new Error(data?.detail||'Componente local indisponível.');}
  return response.json();
}
