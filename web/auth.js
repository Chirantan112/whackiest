(() => {
const signupTab=document.getElementById("signupTab"),loginTab=document.getElementById("loginTab");
const signupForm=document.getElementById("signupForm"),loginForm=document.getElementById("loginForm");
const message=document.getElementById("authMessage"),params=new URLSearchParams(location.search);
function say(text,success=false){message.textContent=text;message.classList.toggle("success",success)}
function setMode(mode){const isSignup=mode==="signup";signupForm.hidden=!isSignup;loginForm.hidden=isSignup;signupTab.classList.toggle("active",isSignup);loginTab.classList.toggle("active",!isSignup);signupTab.setAttribute("aria-selected",String(isSignup));loginTab.setAttribute("aria-selected",String(!isSignup));say("")}
function redirect(user){const fallback=user.role==="employer"?"/employer":"/worker",next=params.get("next");location.assign(next&&next.startsWith("/")&&!next.startsWith("//")?next:fallback)}
async function submit(url,payload,button){button.disabled=true;say("Please wait…");try{const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},credentials:"same-origin",body:JSON.stringify(payload)}),d=await r.json();if(!r.ok)throw Error(d.detail||"Unable to continue.");redirect(d.user)}catch(e){say(e.message)}finally{button.disabled=false}}
signupTab.addEventListener("click",()=>setMode("signup"));loginTab.addEventListener("click",()=>setMode("login"));
if(["worker","employer"].includes(params.get("role")))document.getElementById("signupRole").value=params.get("role");
signupForm.addEventListener("submit",e=>{e.preventDefault();submit("/api/auth/signup",{display_name:document.getElementById("signupName").value.trim(),email:document.getElementById("signupEmail").value.trim(),password:document.getElementById("signupPassword").value,role:document.getElementById("signupRole").value},document.getElementById("signupButton"))});
loginForm.addEventListener("submit",e=>{e.preventDefault();submit("/api/auth/login",{email:document.getElementById("loginEmail").value.trim(),password:document.getElementById("loginPassword").value},document.getElementById("loginButton"))});
})();