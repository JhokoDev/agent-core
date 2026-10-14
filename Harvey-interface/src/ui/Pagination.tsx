export default function Pagination({offset,total,busy,onPage}: {offset:number;total:number;busy?:boolean;onPage:(offset:number)=>void}) {
  return <div className="pagination"><span>{total ? `${offset+1}–${Math.min(offset+20,total)} de ${total}` : 'Nenhum resultado'}</span>
    <button className="text-button" disabled={busy || offset===0} onClick={()=>onPage(Math.max(0,offset-20))}>Anterior</button>
    <button className="text-button" disabled={busy || offset+20>=total} onClick={()=>onPage(offset+20)}>Próxima</button>
  </div>;
}
