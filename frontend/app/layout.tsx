import './globals.css';
import type {Metadata} from 'next';
export const metadata:Metadata={title:'BIST 100 · Paper Trading',description:'Sentetik verilerle sanal işlem ve strateji araştırma terminali'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="tr"><body>{children}</body></html>}
