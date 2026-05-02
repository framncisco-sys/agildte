# Programador: Oscar Amaya Romero
import tkinter as tk
from tkinter import messagebox
from database import conectar

def guardar_producto():
    # Esta función guarda lo que escribas o escanees
    codigo = entry_codigo.get()
    nombre = entry_nombre.get()
    precio = entry_precio.get()

    conexion = conectar()
    if conexion:
        cur = conexion.cursor()
        try:
            cur.execute("INSERT INTO productos (empresa_id, codigo_barra, nombre, precio_unitario) VALUES (1, %s, %s, %s)", 
                        (codigo, nombre, precio))
            conexion.commit()
            messagebox.showinfo("AZ DIGITAL", "¡Producto Guardado con Éxito!")
            # Limpiar para el siguiente producto
            entry_codigo.delete(0, tk.END)
            entry_nombre.delete(0, tk.END)
            entry_precio.delete(0, tk.END)
            entry_codigo.focus() # Pone el cursor listo para el escáner otra vez
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")
        finally:
            conexion.close()

# --- DISEÑO DE LA VENTANA ---
ventana = tk.Tk()
ventana.title("AZ DIGITAL - El Salvador")
ventana.geometry("400x400")

tk.Label(ventana, text="AZ DIGITAL", font=("Arial", 20, "bold"), fg="blue").pack(pady=20)

tk.Label(ventana, text="1. ESCANEA EL PRODUCTO:").pack()
entry_codigo = tk.Entry(ventana, font=("Arial", 14), bg="lightyellow")
entry_codigo.pack(pady=5)
entry_codigo.focus() # Esto es para que el escáner funcione de entrada

tk.Label(ventana, text="2. NOMBRE DEL PRODUCTO:").pack()
entry_nombre = tk.Entry(ventana, width=30)
entry_nombre.pack(pady=5)

tk.Label(ventana, text="3. PRECIO DE VENTA ($):").pack()
entry_precio = tk.Entry(ventana, width=15)
entry_precio.pack(pady=5)

tk.Button(ventana, text="GUARDAR EN INVENTARIO", command=guardar_producto, bg="green", fg="white", height=2).pack(pady=20)

ventana.mainloop()