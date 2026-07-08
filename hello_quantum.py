import os

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler


def main():
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()

    token = os.environ.get("IBM_QUANTUM_TOKEN")
    if not token:
        raise RuntimeError(
            "IBM_QUANTUM_TOKEN is not set. Add it to your shell environment "
            "before running this script."
        )

    service = QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=token,
    )
    backend = service.least_busy(operational=True, simulator=False)

    pass_manager = generate_preset_pass_manager(
        backend=backend,
        optimization_level=1,
    )
    hardware_circuit = pass_manager.run(circuit)

    sampler = Sampler(mode=backend)
    sampler.options.default_shots = 1024

    print(f"Running on {backend.name}")
    print(hardware_circuit)

    job = sampler.run([hardware_circuit])
    print(f"Job ID: {job.job_id()}")

    result = job.result()[0]
    print(result.data.meas.get_counts())


if __name__ == "__main__":
    main()
