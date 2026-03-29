// tvtt-state.js v4.0 — Tartantis VTT — Estado global (sem localStorage)
let _ws=null,_wsRoom=null,_wsCbs={},_wsStateOnce=null,_wsPending=[];
function _wsSend(msg){if(_ws&&_ws.readyState===WebSocket.OPEN)_ws.send(JSON.stringify(msg));else _wsPending.push(msg);}
function _wsConnect(room,callbacks,onStateLoaded){
  _wsRoom=room;_wsCbs=callbacks||{};_wsStateOnce=onStateLoaded||null;
  const proto=location.protocol==='https:'?'wss:':'ws:';
  const wsPort = location.port || (proto === 'wss:' ? '443' : '80');
  const url=`${proto}//${location.hostname}:${wsPort}/ws`;
  _ws=new WebSocket(url);
  _ws.onopen=()=>{_ws.send(JSON.stringify({type:'join',room}));_wsPending.forEach(m=>_ws.send(JSON.stringify(m)));_wsPending=[];};
  _ws.onmessage=evt=>{
    let msg;try{msg=JSON.parse(evt.data);}catch(e){return;}
    const{type,data}=msg;
    if(type==='state'){if(_wsStateOnce){_wsStateOnce(data||{});_wsStateOnce=null;}return;}
    if(type==='map'&&_wsCbs.onMapUpdate)_wsCbs.onMapUpdate(data||{});
    if(type==='token_set'&&_wsCbs.onTokenSet)_wsCbs.onTokenSet(data);
    if(type==='token_remove'&&_wsCbs.onTokenRemove)_wsCbs.onTokenRemove(data&&data.id);
    if(type==='chat'&&_wsCbs.onChatNew)_wsCbs.onChatNew(data);
    if(type==='init'&&_wsCbs.onInitUpdate)_wsCbs.onInitUpdate(data||[]);
    if(type==='init_turn'&&_wsCbs.onInitTurnUpdate)_wsCbs.onInitTurnUpdate(data);
    if(type==='blind_roll'&&_wsCbs.onBlindRollUpdate)_wsCbs.onBlindRollUpdate(data);
    if(type==='char_update'&&_wsCbs.onCharUpdate)_wsCbs.onCharUpdate(data);
  };
  _ws.onclose=()=>{setTimeout(()=>{if(_wsRoom)_wsConnect(_wsRoom,_wsCbs,null);},3000);};
  _ws.onerror=()=>{};
}

// ── Helpers internos ──────────────────────────────────────
function _apiGet(url,cb,fallback){
  fetch(url).then(r=>r.ok?r.json():null).then(d=>cb(d!=null?d:fallback)).catch(()=>cb(fallback));
}
function _apiPost(url,data){
  fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).catch(()=>{});
}

const MBState={
  // ── Sessão: apenas memória, sem persistência ───────────
  session:{
    _data:{},
    get(){return this._data;},
    set(d){this._data=d||{};},
    merge(d){this._data={...this._data,...d};},
    clear(){this._data={};}
  },

  // ── Mesa (campanha) — persiste via /api/save ──────────
  table:{
    KEY:'mb_table_v2',
    _genCode(){return'MB'+Math.random().toString(36).substr(2,5).toUpperCase();},
    get(){return this._cache||null;},
    _cache:null,
    save(data){
      this._cache=data;
      fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).catch(()=>{});
    },
    loadFromDisk(cb){
      fetch('/api/load').then(r=>r.ok?r.json():null).then(data=>{
        this._cache=data;cb(data);
      }).catch(()=>cb(null));
    },
    create(name){
      const t={name:name||'Mesa Virtual',createdAt:Date.now(),players:[],salaCode:this._genCode()};
      this.save(t);return t;
    },
    addPlayer(name,color){
      const t=this.get()||{name:'Mesa',createdAt:Date.now(),players:[],salaCode:this._genCode()};
      const p={id:'p_'+Date.now(),name,color:color||'#c84040'};
      t.players.push(p);this.save(t);return p;
    },
    removePlayer(id){
      const t=this.get();if(!t)return;
      t.players=t.players.filter(p=>p.id!==id);this.save(t);
    },
    reset(){
      this._cache=null;
      fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:'null'}).catch(()=>{});
    },
    getSalaCode(){const t=this.get();return t?t.salaCode:null;}
  },

  // ── Fichas: salvas no servidor em data/rooms/{code}/chars/ ──
  char:{
    default(id){
      return{id:id||('char_'+Date.now()),nome:'',raca:'',classe:'',nivel:1,xp:0,origem:'',
        for:10,des:10,con:10,int:10,sab:10,car:10,pv:20,pvMax:20,pm:10,pmMax:10,
        defesa:10,iniciativa:0,velocidade:9,ataqueCac:'+0',danoCac:'1d6',
        ataqueDist:'+0',danoDist:'1d6',pericias:'',equipamentos:'',poderes:'',notas:''};
    },
    // Carrega ficha do servidor (async)
    load(charId,cb){
      const code=_wsRoom||'LOCAL';
      _apiGet(`/api/room/${code}/char/${charId}`,data=>{
        cb(data&&typeof data==='object'?{...this.default(charId),...data}:this.default(charId));
      },this.default(charId));
    },
    // Salva ficha no servidor (fire-and-forget)
    save(char){
      const code=_wsRoom||'LOCAL';
      _apiPost(`/api/room/${code}/char/${char.id}`,char);
    }
  },

  // ── Mapa: estado sincronizado via WS, persistido pelo servidor ──
  map:{
    default(){return{tokens:[],gridSize:50,showGrid:true,fogActive:false,bgColor:'#1c1712',bgImage:null,panX:0,panY:0};},
    save(code,data){
      if(!code||code==='LOCAL')return;
      const{tokens:_t,...settings}=data;
      _wsSend({type:'map',room:code,data:settings});
    }
  },

  // ── Chat: WS envia ao servidor que persiste em data/rooms/{code}/chat.json ──
  chat:{
    // Carrega histórico do servidor (async)
    get(code,cb){
      _apiGet(`/api/room/${code}/chat`,cb,[]);
    },
    add(code,entry){
      entry={...entry,ts:Date.now(),msgId:Math.random().toString(36).substr(2,10)};
      if(code&&code!=='LOCAL')_wsSend({type:'chat',room:code,data:entry});
      return entry;
    }
  },

  // ── Iniciativa: estado WS, persistido pelo servidor ──
  initiative:{
    save(code,list){
      if(code&&code!=='LOCAL')_wsSend({type:'init',room:code,data:list});
    },
    clear(code){
      if(code&&code!=='LOCAL')_wsSend({type:'init',room:code,data:[]});
    }
  },

  startSync(code,callbacks,onStateLoaded){
    if(!code||code==='LOCAL'){if(onStateLoaded)onStateLoaded({});return;}
    _wsConnect(code,callbacks,onStateLoaded);
    console.log('[MB] WS sync:',code);
  }
};

MBState.tokens={
  saveOne(code,token){if(!code||code==='LOCAL'||!token||!token.id)return;_wsSend({type:'token_set',room:code,data:token});},
  removeOne(code,tokenId){if(!code||code==='LOCAL'||!tokenId)return;_wsSend({type:'token_remove',room:code,data:{id:tokenId}});}
};

// ── Lista de fichas: salva no servidor em data/rooms/{code}/charslist/ ──
MBState.charList={
  load(code,pid,cb){
    _apiGet(`/api/room/${code}/charlist/${pid}`,data=>{
      cb(Array.isArray(data)?data:[]);
    },[]);
  },
  save(code,pid,list){
    _apiPost(`/api/room/${code}/charlist/${pid}`,list);
  }
};

MBState.auth={
  current(){return null;},
  onState(cb){cb(null);},
  signIn(){return Promise.reject(new Error('Use auth local'));},
  signUp(){return Promise.reject(new Error('Use auth local'));},
  signOut(){return Promise.resolve();}
};

MBState.userTable={
  load(uid,cb){
    fetch('/api/load').then(r=>r.ok?r.json():null).then(data=>cb(data,false)).catch(()=>cb(null,false));
  },
  save(uid,data){
    return fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).catch(e=>Promise.reject(e));
  },
  create(uid,name){
    const salaCode=MBState.table._genCode();
    const d={name:name||'Mesa',createdAt:Date.now(),players:[],salaCode,ownerUid:uid};
    return{table:d,fbPromise:this.save(uid,d)};
  },
  addPlayer(uid,data,name,color){
    const p={id:'p_'+Date.now(),name,color:color||'#c84040'};
    const u={...data,players:[...(data.players||[]),p]};
    this.save(uid,u);return u;
  },
  removePlayer(uid,data,pid){
    const u={...data,players:(data.players||[]).filter(p=>p.id!==pid)};
    this.save(uid,u);return u;
  },
  reset(uid){this.save(uid,null).catch(()=>{});}
};

const Dice={
  roll(s){return Math.floor(Math.random()*s)+1;},
  rollN(q,s){const r=[];for(let i=0;i<q;i++)r.push(this.roll(s));return r;},
  parse(expr){
    expr=String(expr).trim().toLowerCase().replace(/\s/g,'');
    if(/^-?\d+$/.test(expr))return{rolls:[],total:parseInt(expr),expr,sides:0,qty:0,mod:0,ok:true};
    const m=expr.match(/^(\d*)d(\d+)([+-]\d+)?$/);
    if(!m)return{ok:false,error:'Expressão inválida: '+expr};
    const qty=Math.min(parseInt(m[1]||'1'),20),sides=parseInt(m[2]),mod=parseInt(m[3]||'0');
    if(qty<1||sides<2)return{ok:false,error:'Dados inválidos'};
    const rolls=this.rollN(qty,sides);
    return{rolls,total:rolls.reduce((a,b)=>a+b,0)+mod,expr,sides,qty,mod,ok:true};
  },
  format(r){
    if(!r.ok)return`❌ ${r.error}`;
    if(!r.rolls.length)return`= **${r.total}**`;
    const ms=r.mod>0?` +${r.mod}`:r.mod<0?` ${r.mod}`:'';
    return`[${r.rolls.join(', ')}]${ms} = **${r.total}**`;
  },
  mod(v){return Math.floor((parseInt(v)-10)/2);},
  modStr(v){const m=this.mod(v);return m>=0?'+'+m:String(m);}
};
