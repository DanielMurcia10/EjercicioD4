# Ejercicio del dia numero 4

# Prompting y fluidez con IA

# chat basado en el prompt malo
Primero Claude lo que hizo fue comenzar a generar codigo que, si, esta bien, funciona y compila correctamente en la terminal pero a la vez,
es un codigo realizado a como el creia conveniente, no ni a lo que quisiera yo ni el cliente, ya que pueda que el cliente hubiera agregado 
otras funciones o tal vez el cliente queria otras funciones y no las que programo Claude.


# chat basado con en la DELEGACION
Este fue el prompt con delegacion que fue lo que le mande a Claude: 

"Aun no sigas programando quiero tener claras cuales seran las funcionalidades para este proyecto, quiero que desglosemos las funciones necesarias, las mas importantes que suele tener una tienda en linea y asignar las tareas que deberia realizar cada uno, ya sea que yo haga la logica de la base de datos y tu programar las funcionalidades, pero antes cuales crees que deberian de ser las otras funciones o apartados que deberia de tener una tienda en linea"

La respuesta que Claude mando despues de haberle escrito el prompt usando delegacion fue una respuesta muy ordenada, no escribio codigo, sino que comenzo
a hacer preguntas clave para la realizacion del proyecto, tratando de aclarar dudas y enlistar las funcionalidades que se adecuaban al proyecto y dejando 
claro que por ejemplo yo realizaria lo que era la logica de la base de datos y el programaria las funcionalidades


# chat basado en la DESCRIPCION
Este fue el prompt con descripcion que le mande a Claude:

"Primero quiero que me des las tres tablas que agregaremos, segundo quiero que actues como un programador con buenas practicas y programa la funcion de agregar al carrito y la funciones que tendra ese carrito ya sea eliminar del carrito, si quiere agregar dos de un mismo producto, la funcionalidad de checkout basico que me mencionaste anteriormente, si en el proceso agregas mas funciones me las haces saber, lo que se busca hacer es una tienda en linea bien estructurada, facil de usar para el usuario"

Le hicimos una descripcion de como queriamos que se viera el producto y rol que queriamos que tomara para este proyecto agregando que le estabamos diciendo lo que hiciera, y su respuesta fue muy ordenada, haciendo uso de las buenas practicas como programador que le dijimos, y esto fue lo que respondio: "separo excepciones propias, estructuras de datos (dataclasses) y lógica de negocio en módulos distintos, en vez de un solo bloque con print() mezclado, así estas funciones se pueden probar y reutilizar sin depender del menú de consola". Y a la vez pidio lo que le solicitamos, y se le dijo que en base lo que fuera programando, que agregara funciones si fueran necesarias y agrego las funciones del carrio como por ejemplo actualizar cantidad y vaciar carrito.


# chat basado en el DISCERNIMIENTO
Este fue el prompt con discernimiento que le mande a Claude:

"antes de copiar y pegar todo en el VSCO, me gustaria que unieras todo, que veas que todo funcione correctamente ya junto, si ves que hay procesos que se tardan demasiado ya sea como un bucle, trata de optimizar el codigo a modo que sea un codigo sostenible y que no de problema, a la vez me gustaria que comentes linea por linea de codigo como buena practica para comentar lo que se hace y si otro desarrollador trabajara en el codigo, que sepa en lo que se ha estado trabajando y como se ha trabajado"

Lo que se buscaba con este prompt es asegurarnos que todo haya quedado bien y que no hayana errores, y que se hace, se le dice a Claude que revise todo y revise si hay funciones que se tardan mas de lo que deberian para optimiza el codigo, que compruebe si todo corre correctamente y si hay algo que fallo mientras se unia, que corrija ese tipo de errores


# chat basado en la DILIGENCA
Este fue el prompt con diligencia que le mande a Claude:

"antes de dar por finalizado este proyecto en el que trabaje contigo, lo sometere a pruebas, si todos los procesos funcionan bien, a la hora de mostrar los resultados en la consola, los muestra de una manera ordenada y sin problemas de compresion, si todas las funcionalidades realizan los procesos sin problemas y tomar responsabilidad de lo que me ayudaste a programar"

Al mandarle este prompt a Claude el mismo se preocupa por el resultado final del proyecto respondiendo lo siguiente: Antes de que hagas tus pruebas, quiero ser transparente sobre qué cubre exactamente lo que ya verifiqué y qué no puedo garantizar desde aquí, y corregir un riesgo real que detecté pensando justo en el punto que mencionas ("sin problemas de comprensión" en consola).

# Mejoro Claude durante el desarrollo del proyecto?
Y la respuesta es que si, al principio Claude nos mando un codigo que la verdad era bastante bueno pero era un codigo sin ideas y sin ningun proposito pero cuando comenzamos a trabajar poco a poco Claude comenzo como a comprometerse mas en el proyecto, aportando mas ideas, agregando mas funcionalidades que serian utiles, pero cuando de verdad fue bastante util fue cuando mande el ultimo prompt que hasta se preocupaba por como se veria el codigo ya en la terminal

