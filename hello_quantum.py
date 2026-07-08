import argparse
import math
import os

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler


def random_bits_circuit(num_bits):
    if num_bits < 1:
        raise ValueError("num_bits must be at least 1")

    circuit = QuantumCircuit(num_bits)
    circuit.h(range(num_bits))
    circuit.measure_all()
    return circuit


def quantum_service():
    token = os.environ.get("IBM_QUANTUM_TOKEN")
    if not token:
        raise RuntimeError(
            "IBM_QUANTUM_TOKEN is not set. Add it to your shell environment "
            "before running this script."
        )

    return QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=token,
    )


def quantum_backend(service):
    return service.least_busy(operational=True, simulator=False)


def backend_num_qubits(backend):
    return getattr(backend, "num_qubits", len(backend.target.qubits))


def quantum_random_bitstrings(num_bits, shots=1, service=None, backend=None):
    if shots < 1:
        raise ValueError("shots must be at least 1")

    service = service or quantum_service()
    backend = backend or quantum_backend(service)
    available_qubits = backend_num_qubits(backend)
    if num_bits > available_qubits:
        raise ValueError(
            f"{backend.name} has {available_qubits} qubits, but this request "
            f"needs {num_bits} qubits."
        )

    circuit = random_bits_circuit(num_bits)
    pass_manager = generate_preset_pass_manager(
        backend=backend,
        optimization_level=1,
    )
    hardware_circuit = pass_manager.run(circuit)

    sampler = Sampler(mode=backend)
    sampler.options.default_shots = shots

    print(f"Running on {backend.name} ({available_qubits} qubits)")
    print(hardware_circuit)

    job = sampler.run([hardware_circuit])
    print(f"Job ID: {job.job_id()}")

    result = job.result()[0]
    return result.data.meas.get_bitstrings()


def quantum_random_int(max_exclusive, shots_per_job=32):
    if max_exclusive < 1:
        raise ValueError("max_exclusive must be at least 1")
    if max_exclusive == 1:
        return 0

    num_bits = math.ceil(math.log2(max_exclusive))
    service = quantum_service()
    backend = quantum_backend(service)
    available_qubits = backend_num_qubits(backend)
    if num_bits > available_qubits:
        max_supported_exclusive = 2**available_qubits
        raise ValueError(
            f"{max_exclusive} needs {num_bits} qubits, but {backend.name} "
            f"has {available_qubits}. The largest supported max_exclusive on "
            f"this backend is {max_supported_exclusive}."
        )

    while True:
        for bitstring in quantum_random_bitstrings(
            num_bits,
            shots=shots_per_job,
            service=service,
            backend=backend,
        ):
            candidate = int(bitstring, 2)
            if candidate < max_exclusive:
                return candidate


def main():
    parser = argparse.ArgumentParser(
        description="Generate a true random integer from IBM Quantum hardware."
    )
    parser.add_argument(
        "max_exclusive",
        nargs="?",
        type=int,
        default=16,
        help="Return an integer from 0 up to, but not including, this value.",
    )
    parser.add_argument(
        "--shots-per-job",
        type=int,
        default=32,
        help="Hardware samples to request per job while rejection sampling.",
    )
    args = parser.parse_args()

    value = quantum_random_int(
        args.max_exclusive,
        shots_per_job=args.shots_per_job,
    )
    print(f"Random integer [0, {args.max_exclusive}): {value}")


if __name__ == "__main__":
    main()
