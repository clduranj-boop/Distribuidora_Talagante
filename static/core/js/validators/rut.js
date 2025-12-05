export function initRutValidation(inputSelector = '[name="rut"]') {
    const input = document.querySelector(inputSelector);
    if (!input) return;

    // Formateo mientras escribe 
    input.addEventListener('input', function () {
        let val = this.value.replace(/[^\dkK]/g, '').toUpperCase();
        if (val.length > 1) {
            const cuerpo = val.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
            const dv = val.slice(-1);
            this.value = `${cuerpo}-${dv}`;
        }
    });

    // Validacion de dígito verificador al salir
    input.addEventListener('blur', function () {
        const rut = this.value.replace(/[^\dkK]/g, '').toUpperCase();
        if (rut.length < 8) return;

        const cuerpo = rut.slice(0, -1);
        let dv = rut.slice(-1);
        let suma = 0;
        let multiplo = 2;

        for (let i = cuerpo.length - 1; i >= 0; i--) {
            suma += multiplo * parseInt(cuerpo.charAt(i), 10);
            multiplo = multiplo < 7 ? multiplo + 1 : 2;
        }

        const dvEsperado = 11 - (suma % 11);
        dv = dv === 'K' ? 10 : (dv === '0' ? 11 : parseInt(dv, 10));
        const valido = dv === dvEsperado;

        input.classList.toggle('is-valid', valido);
        input.classList.toggle('is-invalid', !valido);
    });
}