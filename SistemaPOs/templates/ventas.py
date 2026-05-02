import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
from database import ConexionDB

class VentanaVentas:
    def __init__(self, root):
        self.root = root
        self.root.title("AZ DIGITAL - Terminal de Ventas")
        self.root.geometry("900x700")
        self.root.configure(bg="#f4f7f6")
        
        self.db = ConexionDB()
        self.carrito = [] # Lista de productos escaneados

        # --- ENCABEZADO ESTILO WEB ---
        self.header = tk.Frame(root, bg="#0056b3", height=70)
        self.header.pack(fill="x")
        tk.Label(self.header, text="AZ DIGITAL | PUNTO DE VENTA", font=("Arial", 18, "bold"), fg="white", bg="#0056b3").pack(pady=20)

        # Botón de Sincronización
        self.btn_sync = tk.Button(root, text="Sincronizar Datos 🔄", command=self.sincronizar_datos, 
                                  bg="#ffc107", font=("Arial", 10, "bold"), relief="flat", cursor="hand2")
        self.btn_sync.pack(pady=10, anchor="e", padx=30)

        # --- ÁREA DE ESCÁNER ---
        self.frame_escanner = tk.Frame(root, bg="#f4f7f6")
        self.frame_escanner.pack(pady=10, fill="x", padx=30)

        tk.Label(self.frame_escanner, text="ESCANEE PRODUCTO:", font=("Arial", 12, "bold"), bg="#f4f7f6").pack(anchor="w")
        self.ent_escanner = tk.Entry(self.frame_escanner, font=("Arial", 20), bg="white", bd=1, relief="solid")
        self.ent_escanner.pack(pady=5, fill="x")
        self.ent_escanner.bind('<Return>', self.buscar_producto)
        self.ent_escanner.focus()

        # --- TABLA DE PRODUCTOS ---
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 12, "bold"))
        style.configure("Treeview", font=("Arial", 11), rowheight=35)
        
        self.tabla = ttk.Treeview(root, columns=("Nombre", "Precio", "Subtotal"), show='headings')
        self.tabla.heading("Nombre", text="DESCRIPCIÓN DEL PRODUCTO")
        self.tabla.heading("Precio", text="PRECIO UNITARIO ($)")
        self.tabla.heading("Subtotal", text="SUBTOTAL ($)")
        self.tabla.column("Nombre", width=400)
        self.tabla.pack(pady=10, fill="both", expand=True, padx=30)

        # --- TOTAL Y COBRO ---
        self.frame_total = tk.Frame(root, bg="#ffffff", bd=1, relief="solid")
        self.frame_total.pack(side="bottom", fill="x", padx=30, pady=20)

        self.lbl_total = tk.Label(self.frame_total, text="TOTAL A PAGAR: $0.00", font=("Arial", 28, "bold"), fg="#28a745", bg="white")
        self.lbl_total.pack(side="left", padx=20, pady=20)

        tk.Button(self.frame_total, text="FINALIZAR Y COBRAR", command=self.finalizar_pago, 
                  bg="#28a745", fg="white", font=("Arial", 16, "bold"), relief="flat", width=20, height=2, cursor="hand2").pack(side="right", padx=20)

    def buscar_producto(self, event):
        codigo = self.ent_escanner.get()
        # Intentamos buscar en la nube (PostgreSQL)
        query = "SELECT nombre, precio_unitario, id FROM productos WHERE codigo_barra = %s"
        # Usamos una conexión rápida solo para lectura
        try:
            conn = self.db.conectar_postgre() # Necesitas este método en database.py
            cur = conn.cursor()
            cur.execute(query, (codigo,))
            res = cur.fetchone()
            if res:
                nombre, precio, p_id = res
                self.tabla.insert("", "end", values=(nombre, f"${precio:.2f}", f"${precio:.2f}"))
                self.carrito.append({"id": p_id, "nombre": nombre, "precio": precio, "codigo": codigo})
                self.actualizar_total()
            else:
                messagebox.showwarning("AZ DIGITAL", "Producto no registrado.")
            cur.close()
            conn.close()
        except:
            messagebox.showerror("Error", "No hay conexión para buscar productos nuevos.")
        
        self.ent_escanner.delete(0, tk.END)

    def actualizar_total(self):
        total = sum(item['precio'] for item in self.carrito)
        self.lbl_total.config(text=f"TOTAL A PAGAR: ${total:.2f}")

    def finalizar_pago(self):
        if not self.carrito:
            messagebox.showwarning("AZ DIGITAL", "El carrito está vacío.")
            return

        total_venta = sum(item['precio'] for item in self.carrito)
        pago_tarjeta = messagebox.askyesno("MÉTODO DE PAGO", "¿El cliente paga con TARJETA?")
        metodo = "TARJETA" if pago_tarjeta else "EFECTIVO"

        # Intentamos guardar
        for item in self.carrito:
            # Mandamos a guardar (database.py decide si es Nube o Local)
            sql = "INSERT INTO ventas (sucursal_id, usuario_id, tipo_pago, total_pagar) VALUES (1, 1, %s, %s)"
            estado = self.db.ejecutar_sql(sql, (metodo, item['precio']))

        messagebox.showinfo("AZ DIGITAL", f"Venta guardada en modo: {estado}")
        self.limpiar_caja()

    def limpiar_caja(self):
        self.tabla.delete(*self.tabla.get_children())
        self.carrito = []
        self.actualizar_total()
        self.ent_escanner.focus()

    def sincronizar_datos(self):
        # Lógica para subir ventas de az_digital_local.db a PostgreSQL
        self.db.sincronizar() 
        messagebox.showinfo("AZ DIGITAL", "Sincronización completada.")