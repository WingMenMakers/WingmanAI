export default function FullScreenLoader() {
    return (
        <div style={styles.container}>
            <div style={styles.spinner} />
            <p style={styles.text}>Loading...</p>
        </div>
    );
}

const styles = {
    container: {
        height: "100vh",
        width: "100vw",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#0f172a",
        color: "#e5e7eb",
    },
    spinner: {
        width: "48px",
        height: "48px",
        border: "5px solid #334155",
        borderTop: "5px solid #38bdf8",
        borderRadius: "50%",
        animation: "spin 1s linear infinite",
    },
    text: {
        marginTop: "12px",
        fontSize: "14px",
        opacity: 0.8,
    },
};
