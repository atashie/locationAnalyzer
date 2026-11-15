const fs=require('fs');
const html=fs.readFileSync(process.argv[2],'utf8');
const js=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].pop()[1];
const els={};const mk=id=>({id,innerHTML:'',textContent:'',hidden:false,attrs:{},setAttribute(k,v){this.attrs[k]=v},
 addEventListener(){},querySelectorAll(){return []}});
global.document={getElementById:id=>els[id]||(els[id]=mk(id))};
global.localStorage={getItem(){return null},setItem(){}};global.location={hash:''};
eval(js + '\n' + fs.readFileSync(__dirname+'/check_page_cases.js','utf8'));
