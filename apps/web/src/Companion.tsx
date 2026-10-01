import React,{useId} from 'react';

export type CompanionProps={variant:'orb'|'receiver';busy?:boolean;size?:'home'|'mini'};
/**
 * CONTINUUM-V1-20261001 native-vector derivatives, not the original artwork.
 * orb: M-01 / ea89c4326d0ba739cab760c7f79fe827802f265a90406184b24c98d1c25d6648
 * receiver: M-02 / c15c106d8d62b5b8aaf33895449530fdcff3c755a775dd9d850a124a76029320
 * Canonical originals remain unchanged in docs/design/continuum-v1/assets/.
 * Retains both candidates. The parent owns A/B/off; this component selects no winner.
 * Decorative only: no microphone, listening, comprehension or completion claim.
 * No idle animation. busy must come from actual pending work, never a decorative timer.
 */
export function Companion({variant,busy=false,size='home'}:CompanionProps){
 const id='continuum-'+useId().replace(/[^a-zA-Z0-9_-]/g,'');
 const paint=(name:string)=>`url(#${id}-${name})`;
 return <span className={`companion companion--${variant} companion--${size}`} data-busy={busy?'true':'false'} data-derivative-of={variant==='orb'?'M-01':'M-02'} aria-hidden="true">
  <svg viewBox="0 0 360 300" xmlns="http://www.w3.org/2000/svg" focusable="false" aria-hidden="true">
   <defs>
    <radialGradient id={`${id}-core`} cx="35%" cy="25%" r="80%"><stop offset="0" stopColor="#e9f4ff"/><stop offset=".26" stopColor="#a1b8ff"/><stop offset=".56" stopColor="#647cdd"/><stop offset=".8" stopColor="#a5b6ed"/><stop offset="1" stopColor="#eef1ff"/></radialGradient>
    <radialGradient id={`${id}-core-light`} cx="80%" cy="22%" r="86%"><stop offset="0" stopColor="#fffced" stopOpacity=".95"/><stop offset=".3" stopColor="#f9e9ff" stopOpacity=".6"/><stop offset=".65" stopColor="#d6dcff" stopOpacity="0"/></radialGradient>
    <linearGradient id={`${id}-shell`} x1=".1" y1=".16" x2=".95" y2=".82" gradientUnits="objectBoundingBox"><stop stopColor="#eff8ff" stopOpacity=".96"/><stop offset=".27" stopColor="#b7c8ff" stopOpacity=".72"/><stop offset=".49" stopColor="#fcfaff" stopOpacity=".48"/><stop offset=".73" stopColor="#c5c5fa" stopOpacity=".65"/><stop offset="1" stopColor="#fef7ed" stopOpacity=".98"/></linearGradient>
    <linearGradient id={`${id}-edge`} x1="0" y1="0" x2="1" y2="1"><stop stopColor="#fffdf4"/><stop offset=".3" stopColor="#fff"/><stop offset=".56" stopColor="#aabffc"/><stop offset=".79" stopColor="#fff"/><stop offset="1" stopColor="#f9e7ed"/></linearGradient>
    <linearGradient id={`${id}-ribbon`} x1="0" y1=".2" x2="1" y2=".8"><stop stopColor="#eef5ff"/><stop offset=".31" stopColor="#bccbff" stopOpacity=".55"/><stop offset=".58" stopColor="#e7e3ff" stopOpacity=".42"/><stop offset=".84" stopColor="#fff8ee" stopOpacity=".88"/><stop offset="1" stopColor="#e0e9ff"/></linearGradient>
    <radialGradient id={`${id}-satellite`} cx="28%" cy="20%" r="86%"><stop stopColor="#fffdf2"/><stop offset=".27" stopColor="#f3f2ff"/><stop offset=".6" stopColor="#a3b8f5"/><stop offset=".8" stopColor="#c5d7fd"/><stop offset="1" stopColor="#fff"/></radialGradient>
    <radialGradient id={`${id}-shadow`}><stop stopColor="#94a5d6" stopOpacity=".25"/><stop offset="1" stopColor="#b5c7f0" stopOpacity="0"/></radialGradient>
    <radialGradient id={`${id}-container`} cx="31%" cy="29%" r="90%"><stop stopColor="#dbe8ff"/><stop offset=".32" stopColor="#a5b7f1"/><stop offset=".6" stopColor="#b0bde8"/><stop offset=".82" stopColor="#e7e7fc"/><stop offset="1" stopColor="#fff9ed"/></radialGradient>
    <linearGradient id={`${id}-aperture`} x1="0" y1="0" x2="0" y2="1"><stop stopColor="#7583b5"/><stop offset=".55" stopColor="#5e698e"/><stop offset="1" stopColor="#abb8df"/></linearGradient>
    <linearGradient id={`${id}-rim`} x1="0" y1="0" x2="1" y2="1"><stop stopColor="#fffef5"/><stop offset=".3" stopColor="#c9d4ff"/><stop offset=".64" stopColor="#fff"/><stop offset="1" stopColor="#e9dfff"/></linearGradient>
   </defs>
   <ellipse className="companion-shadow" cx="179" cy="268" rx={variant==='orb'?104:128} ry="18" fill={paint('shadow')}/>
   {variant==='orb'?<g className="companion-body companion-orb-body">
    {/* The enclosure is deliberately off-axis and unequal, not a stock concentric ball. */}
    <path className="companion-shell" d="M100 198C58 186 67 138 104 87C139 39 196 14 222 31C246 47 232 87 216 126C249 120 290 133 302 160C319 195 273 235 217 248C160 262 98 233 100 198Z" fill={paint('shell')} stroke={paint('edge')} strokeWidth="2"/>
    <path d="M101 198C77 166 101 111 133 75C163 42 199 26 217 32C185 18 129 57 97 102C61 153 73 184 101 198Z" fill="#d4e4ff" fillOpacity=".44"/>
    <path d="M107 190C75 159 93 102 132 70C171 38 216 21 226 42" fill="none" stroke="#fff" strokeOpacity=".78" strokeWidth="3" strokeLinecap="round"/>
    <circle className="companion-core" cx="176" cy="149" r="70" fill={paint('core')} stroke="#eef3ff" strokeWidth="2"/>
    <circle cx="176" cy="149" r="70" fill={paint('core-light')}/>
    <path d="M120 133C122 106 143 86 167 83" fill="none" stroke="#faffff" strokeOpacity=".82" strokeWidth="3.5" strokeLinecap="round"/>
    <path d="M127 194C150 220 188 224 215 198" fill="none" stroke="#e4efff" strokeOpacity=".66" strokeWidth="2"/>
    {/* Single material reflection: no paired highlights, face, pupil or gaze. */}
    <path d="M120 161C122 151 133 151 141 157C152 165 157 180 153 192C149 203 138 206 130 197C122 188 118 172 120 161Z" fill={paint('satellite')} stroke="#f4f7ff" strokeOpacity=".92"/>
    <path className="companion-ribbon" d="M77 155C50 177 77 209 137 218C196 228 267 208 296 179C307 168 310 158 301 148C310 174 261 194 206 201C149 209 107 196 91 179C85 172 82 162 77 155Z" fill={paint('ribbon')} stroke={paint('edge')} strokeWidth="1.8"/>
    <path d="M75 157C57 186 115 218 177 216C237 214 289 190 301 170" fill="none" stroke="#fff" strokeOpacity=".92" strokeWidth="2.4"/>
    <path d="M89 183C92 218 119 245 150 253C182 261 218 249 246 226" fill="none" stroke={paint('edge')} strokeWidth="2"/>
    <g className="companion-satellites"><circle cx="59" cy="206" r="14" fill={paint('satellite')} stroke="#fff" strokeWidth="1.5"/><circle cx="285" cy="83" r="11" fill={paint('satellite')} stroke="#fff" strokeWidth="1.4"/><circle cx="266" cy="254" r="8" fill={paint('satellite')} stroke="#fff" strokeWidth="1.2"/></g>
   </g>:<g className="companion-body companion-receiver-body">
    {/* Open receiving aperture and soft container; no animated files or absorption claim. */}
    <path className="companion-shell" d="M82 118C101 85 147 70 192 75C249 73 287 99 302 147C314 184 309 223 280 242C249 263 179 271 126 258C80 247 57 225 59 190C60 164 66 139 82 118Z" fill={paint('container')} stroke={paint('edge')} strokeWidth="2"/>
    <path d="M92 113C113 85 165 79 207 84C248 87 278 105 286 131C258 146 234 147 206 132C165 108 130 105 92 113Z" fill={paint('shell')} stroke={paint('edge')} strokeWidth="1.6"/>
    <path d="M117 103C139 93 191 92 225 100C248 105 263 112 257 119C250 128 208 127 176 122C143 117 111 113 117 103Z" fill={paint('aperture')} stroke={paint('rim')} strokeWidth="4"/>
    <path d="M115 104C139 90 191 91 229 100" fill="none" stroke="#fff" strokeOpacity=".88" strokeWidth="2.5" strokeLinecap="round"/>
    <path className="companion-ribbon" d="M74 133C97 115 127 120 164 146C209 177 264 178 303 159C308 187 309 215 289 236C243 257 206 261 166 247C114 232 106 203 79 190C67 184 60 184 59 195C59 171 62 151 74 133Z" fill={paint('ribbon')} stroke={paint('edge')} strokeWidth="1.8"/>
    <path d="M73 134C106 112 158 151 196 165C233 178 275 177 301 162" fill="none" stroke="#fff" strokeOpacity=".84" strokeWidth="2.5" strokeLinecap="round"/>
    <path d="M63 196C67 234 105 254 154 261C204 267 263 252 283 242" fill="none" stroke="#fffaf2" strokeOpacity=".84" strokeWidth="2.3"/>
    {/* A broad surface seam replaces the board's eye-like circular front indicator. */}
    <path d="M89 168C86 186 89 201 99 212" fill="none" stroke="#f3f8ff" strokeOpacity=".88" strokeWidth="4" strokeLinecap="round"/>
    <path d="M265 121C279 126 292 142 296 155" fill="none" stroke="#fffef5" strokeOpacity=".76" strokeWidth="3" strokeLinecap="round"/>
   </g>}
  </svg>
 </span>;
}
