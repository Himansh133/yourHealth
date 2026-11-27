import { useId } from "react";

export type HealthArea = "heart" | "metabolic" | "kidney";

/** Original, decorative anatomy artwork. Its neighbouring buttons carry the interaction. */
export default function HealthIllustration({ active }: { active: HealthArea }) {
  const id = useId().replace(/:/g, "");
  const ref = (name: string) => `url(#${id}-${name})`;
  return <svg className="health-illustration" viewBox="0 0 520 630" fill="none" aria-hidden="true">
    <defs>
      <linearGradient id={`${id}-body`} x1="170" y1="90" x2="345" y2="600" gradientUnits="userSpaceOnUse">
        <stop stopColor="#afcad0" stopOpacity=".72" /><stop offset=".45" stopColor="#d6e6e8" stopOpacity=".62" /><stop offset="1" stopColor="#e7f0ef" stopOpacity=".1" />
      </linearGradient>
      <linearGradient id={`${id}-organ`} x1="220" y1="220" x2="290" y2="370" gradientUnits="userSpaceOnUse">
        <stop stopColor="#d88b84" /><stop offset="1" stopColor="#a65757" />
      </linearGradient>
      <linearGradient id={`${id}-kidney`} x1="217" y1="355" x2="300" y2="395" gradientUnits="userSpaceOnUse">
        <stop stopColor="#bd8270" /><stop offset="1" stopColor="#9d6658" />
      </linearGradient>
      <radialGradient id={`${id}-halo`}><stop stopColor="#d8e9e5" stopOpacity=".9" /><stop offset="1" stopColor="#e8f1ed" stopOpacity="0" /></radialGradient>
      <radialGradient id={`${id}-cell`}><stop stopColor="#e7aaa3" /><stop offset="1" stopColor="#ba746c" /></radialGradient>
      <linearGradient id={`${id}-fade`} x1="0" y1="490" x2="0" y2="625" gradientUnits="userSpaceOnUse"><stop stopColor="white" /><stop offset="1" stopColor="black" /></linearGradient>
      <mask id={`${id}-body-mask`}><rect width="520" height="630" fill="white" /><rect y="490" width="520" height="140" fill={ref("fade")} /></mask>
    </defs>
    <ellipse cx="262" cy="326" rx="237" ry="269" fill={ref("halo")} />
    <g className="anatomy-orbits" stroke="#9eb9b0" strokeOpacity=".45">
      <ellipse cx="260" cy="320" rx="178" ry="207" strokeDasharray="3 8" />
      <ellipse cx="260" cy="320" rx="212" ry="150" transform="rotate(-35 260 320)" strokeOpacity=".25" />
      <ellipse cx="260" cy="320" rx="219" ry="178" transform="rotate(40 260 320)" strokeOpacity=".18" />
      <circle cx="84" cy="315" r="4" fill="#f6faf7" /><circle cx="400" cy="190" r="4" fill="#f6faf7" /><circle cx="306" cy="519" r="4" fill="#f6faf7" />
    </g>
    <path d="M139 185 213 250M378 197 291 280M102 399 222 379M384 438 287 382" stroke="#94afa4" strokeWidth="1.2" strokeDasharray="3 5" />
    <g mask={ref("body-mask")}>
      <path d="M241 155 240 174C231 182 216 182 203 187 187 193 178 214 174 236L153 326 143 403 147 426 156 428 165 412 176 349 198 281 201 348 191 407 202 471 211 581 231 589 240 499 251 436 260 430 272 441 280 502 286 587 305 581 315 472 326 409 317 348 319 281 341 349 351 413 360 429 370 424 374 402 364 326 343 237C338 214 331 193 314 188 301 183 287 182 279 174L278 154Z" fill={ref("body")} stroke="#91adb8" strokeOpacity=".42" strokeWidth="1.3" />
      <path d="M228 115C226 90 240 73 260 73 282 73 294 90 293 115L289 139C284 157 273 168 260 168 247 168 235 156 231 140Z" fill={ref("body")} stroke="#8eacb5" strokeOpacity=".48" strokeWidth="1.3" />
      <path d="m237 119 9-3 8 3m13 0 8-3 9 3m-25 4-3 16 7 1m-14 10q11 5 20 0m-27-39q17-7 35 0" stroke="#f1f7f8" strokeWidth="1.2" strokeLinecap="round" />
      <path d="M260 170V247M204 209 242 197 259 207 277 196 316 209M217 217 231 286M301 217 289 286M207 324Q260 350 314 324M209 343Q260 367 313 343" stroke="#f4f9f8" strokeWidth="1.2" strokeOpacity=".85" />
      <g opacity=".32" stroke="#8ca6b0" strokeWidth="1.2">
        <path d="M260 176V428m-22-203h45m-47 14h49m-51 14h53m-55 14h57m-57 14h57m-55 14h53m-51 14h49m-44 14h39m-36 14h33m-29 14h25m-23 14h21" />
        <path d="M257 219Q227 204 210 225m47 9q-33-12-47 7m47 8q-34-11-48 8m48 6q-34-10-48 8m54-52q29-14 48 7m-48 8q31-12 49 7m-49 8q32-11 50 8m-50 6q32-10 50 8" />
      </g>
      <g className={`anatomy-lungs ${active === "heart" ? "is-highlighted" : ""}`}>
        <path d="M247 219C231 213 214 231 210 249 204 275 210 303 227 310 239 315 250 305 250 292V235Z" fill="#d3a09a" fillOpacity=".72" stroke="#f7ded8" strokeWidth="1.2" />
        <path d="M272 219C289 213 305 232 310 251 317 275 308 304 291 310 280 313 270 302 270 291V235Z" fill="#d3a09a" fillOpacity=".72" stroke="#f7ded8" strokeWidth="1.2" />
        <path d="M260 195V242m0-9-18 20m18-20 18 20m-36 0-13 10m13-10 2 19m34-19 13 12m-13-12-1 18" stroke="#f3e7e1" strokeWidth="3.2" strokeLinecap="round" />
      </g>
      <g className={`anatomy-heart ${active === "heart" ? "is-highlighted" : ""}`}>
        <path d="M252 259C241 246 231 257 235 274 238 289 251 299 264 304 276 293 283 276 277 265 272 256 261 255 256 263Z" fill={ref("organ")} stroke="#f2d0c7" strokeWidth="1.2" />
        <path d="m254 265-2-18 6-6m4 23 5-19 7-2m-24 39 13-7 9 9" stroke="#ecd2c8" strokeWidth="2.8" strokeLinecap="round" />
      </g>
      <g className={`anatomy-metabolic ${active === "metabolic" ? "is-highlighted" : ""}`}>
        <path d="M213 319C231 308 264 308 284 318L297 330C274 338 253 346 235 341L214 333Z" fill="#b97b6d" stroke="#efd4c6" strokeWidth="1.1" />
        <path d="M279 332C297 331 307 347 300 362 295 374 282 379 267 372 256 368 249 357 253 350 258 341 271 348 277 342Z" fill="#d8afa0" stroke="#f3ddd3" />
        <path d="M224 400C218 386 229 379 242 383L275 382C292 380 302 393 297 409L292 435C286 450 233 449 227 436Z" fill="#c68e7e" fillOpacity=".7" stroke="#f0d5c7" />
        <path d="M235 392Q247 386 250 397T268 399T285 394M234 407Q249 397 249 411T269 414T286 407M236 425Q246 414 251 427T270 427T285 423" stroke="#f4d9ca" strokeWidth="4.5" strokeLinecap="round" />
      </g>
      <g className={`anatomy-kidney ${active === "kidney" ? "is-highlighted" : ""}`}>
        <path d="M225 352C210 350 207 366 213 378 216 385 225 385 230 380 233 374 223 374 225 368 233 362 231 355 225 352Z" fill={ref("kidney")} stroke="#efd7c7" />
        <path d="M295 352C310 350 313 366 307 378 304 385 295 385 290 380 287 374 297 374 295 368 287 362 289 355 295 352Z" fill={ref("kidney")} stroke="#efd7c7" />
        <path d="M225 370q15 20 23 50m47-50q-16 20-23 50" stroke="#dfc7b5" strokeWidth="1.5" />
      </g>
      <path d="M248 177 247 217M272 177 273 217M197 227 181 316 161 393M323 227 338 316 357 393M213 451 224 566M307 451 297 566" stroke="#adc2c7" strokeOpacity=".45" strokeWidth="2" />
    </g>
    <g className="anatomy-cell anatomy-cell-top" transform="translate(101 163)">
      <circle r="35" fill="#f8fbf8" fillOpacity=".9" stroke="#d0dfd8" />
      {[[0,-15],[-13,-8],[13,-7],[-15,8],[1,3],[15,10],[-3,18]].map(([x,y],i)=><g key={i}><circle cx={x} cy={y} r="7" fill={ref("cell")} /><circle cx={x} cy={y} r="3" stroke="#f1d1c9" strokeWidth="1.5" /></g>)}
    </g>
    <g className="anatomy-cell anatomy-cell-bottom" transform="translate(403 425)">
      <circle r="32" fill="#f8fbf8" fillOpacity=".9" stroke="#d0dfd8" />
      <path d="m-16 8 9-23 11 27 10-21 6 24M-22-5 22 3m-43 10 40-28" stroke="#c4807b" strokeWidth="5" strokeLinecap="round" />
      <path d="m-15 17 5-27 16 25 11-29M-23 5 20-7" stroke="#86a5b5" strokeWidth="3" strokeLinecap="round" />
    </g>
    <circle cx="260" cy="279" r="29" className="anatomy-pulse" stroke="#b98078" strokeOpacity=".3" />
  </svg>;
}
