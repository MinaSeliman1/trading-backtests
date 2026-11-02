"""Interactive local subscription only: the topic never goes to stdout/files."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'runtime/vendor'),str(ROOT.parents[2]/'.python_packages')]

def main():
 import tkinter as tk
 from tkinter import messagebox
 from qqq_alerts.setup import TopicStore
 from qqq_alerts.transport import Ntfy
 from qqq_alerts.outbox import atomic
 from datetime import datetime,timezone
 topics=TopicStore().load()
 if topics is None:raise RuntimeError('notification configuration missing')
 app=tk.Tk();app.title('QQQ SIMULATION - ABONNEMENT AUX ALERTES');app.geometry('680x760');app.resizable(False,False)
 text='1. Installe ntfy sur ton telephone et autorise les notifications.\n2. Ajoute un abonnement : serveur https://ntfy.sh ; sujet ci-dessous.\nLe QR ouvre son adresse Web, depuis laquelle tu peux copier le sujet.\nAndroid : active Instant delivery pour limiter les retards.'
 tk.Label(app,text=text,justify='left',wraplength=640,padx=15,pady=15).pack()
 var=tk.StringVar(value=topics['alert']);field=tk.Entry(app,textvariable=var,width=64,state='readonly');field.pack(pady=4)
 def copy():app.clipboard_clear();app.clipboard_append(topics['alert']);app.update()
 tk.Button(app,text='Copier le sujet (garder cette adresse hors du chat/GitHub)',command=copy).pack(pady=4)
 try:
  import qrcode
  from PIL import ImageTk
  photo=ImageTk.PhotoImage(qrcode.make('https://ntfy.sh/'+topics['alert']).get_image().resize((330,330)))
  label=tk.Label(app,image=photo);label.image=photo;label.pack(pady=8)
 except ImportError:
  tk.Label(app,text='QR facultatif indisponible : utilise le sujet copiable ci-dessus.',wraplength=640,pady=40).pack()
 result=tk.StringVar(value='Reception sur telephone : non confirmee.')
 def test():
  try:
   Ntfy(**topics).test();atomic(ROOT/'runtime/phone_test.json',dict(server_accepted=True,utc=datetime.now(timezone.utc).isoformat(),phone_received=False));result.set('Test accepte par ntfy. Verifie maintenant ton telephone.')
  except Exception:messagebox.showerror('Notification','Envoi impossible. Aucun detail sensible affiche.')
 def received():
  atomic(ROOT/'runtime/phone_receipt.json',dict(user_confirmed_received=True,utc=datetime.now(timezone.utc).isoformat(),simulation_only=True));result.set('Reception confirmee par toi. Merci. Tu peux fermer cette fenetre.')
 tk.Button(app,text='3. Envoyer un TEST aux deux bots',command=test).pack(pady=6)
 tk.Button(app,text='4. Je confirme avoir recu le TEST sur mon telephone',command=received).pack(pady=6)
 tk.Label(app,textvariable=result,wraplength=640).pack(pady=6)
 tk.Label(app,text='Sujet non reserve : toute personne connaissant son adresse peut le lire.\nLes messages ne contiennent ni cle, ni compte, ni quantite, ni P&L.',fg='gray',wraplength=640).pack(pady=6)
 atomic(ROOT/'runtime/subscription_ui.json',dict(window_opened=True,values_output=False));app.mainloop()
if __name__=='__main__':
 try:main()
 except Exception as e:
  from qqq_alerts.outbox import atomic
  atomic(ROOT/'runtime/subscription_ui.json',dict(window_opened=False,error_type=type(e).__name__,values_output=False))
