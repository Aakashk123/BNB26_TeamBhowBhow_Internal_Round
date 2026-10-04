// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

/// @notice Anchors claims, identities and independent corroborations. Does not identify models from pixels.
contract ModelLedgerRegistry is EIP712, AccessControl {
    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");
    bytes32 public constant WITNESS_ADMIN_ROLE = keccak256("WITNESS_ADMIN_ROLE");
    bytes32 private constant EVENT_TYPEHASH = keccak256("Event(bytes32 actorId,uint8 action,bytes32 modelRef,bytes32[] parentEventIds,bytes32[] inputSha256,bytes32 outputSha256,bytes32 outputPixelSha256,uint64 outputPHash,bytes32 paramsHash,bytes32 privateRoot,uint64 claimedAt,bytes32 nonce)");
    bytes32 private constant WITNESS_TYPEHASH = keccak256("Witness(bytes32 eventHash,uint8 kind,bytes32 evidenceHash)");
    struct Actor { address signer; bytes32 orgId; bytes32 modelMeasurement; uint8 status; uint64 approvedAt; uint64 revokedFrom; }
    struct EventData {
        bytes32 actorId; uint8 action; bytes32 modelRef; bytes32[] parentEventIds; bytes32[] inputSha256;
        bytes32 outputSha256; bytes32 outputPixelSha256; uint64 outputPHash; bytes32 paramsHash;
        bytes32 privateRoot; uint64 claimedAt; bytes32 nonce;
    }
    struct Anchor { bytes32 actorId; uint64 blockTime; uint64 blockNumber; }
    struct WitnessInfo { bytes32 orgId; bool approved; }
    struct WitnessRecord { address signer; bytes32 orgId; uint8 kind; bytes32 evidenceHash; uint64 blockTime; }
    struct Batch { address signer; uint64 blockTime; uint32 count; string uri; }
    mapping(bytes32 => Actor) private actors;
    mapping(bytes32 => Anchor) private anchors;
    mapping(bytes32 => bytes32) public firstClaim;
    mapping(address => WitnessInfo) public witnesses;
    mapping(bytes32 => mapping(bytes32 => bool)) public witnessedBy;
    mapping(bytes32 => WitnessRecord[]) private records;
    mapping(bytes32 => Batch) public batches;
    address public issuer;
    event ActorRegistered(bytes32 indexed actorId, address signer, bytes32 orgId);
    event ActorApproved(bytes32 indexed actorId);
    event ActorRevoked(bytes32 indexed actorId, uint64 effectiveFrom);
    event EventAnchored(bytes32 indexed eventHash, bytes32 indexed actorId, bytes32 indexed outputSha256);
    event Witnessed(bytes32 indexed eventHash, address indexed signer, bytes32 orgId, uint8 kind, bytes32 evidenceHash);
    event BatchAnchored(bytes32 indexed root, uint32 count, string uri);
    event IssuerSet(address indexed issuerAddress);
    constructor(address admin) EIP712("ModelLedger", "1") {
        require(admin != address(0), "ZERO_ADMIN");
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(REGISTRAR_ROLE, admin);
        _grantRole(WITNESS_ADMIN_ROLE, admin);
    }
    function registerActor(bytes32 id, bytes32 org, bytes32 measurement) external {
        require(id != bytes32(0) && org != bytes32(0), "EMPTY_ID");
        require(actors[id].signer == address(0), "ACTOR_EXISTS");
        actors[id] = Actor(msg.sender, org, measurement, 1, 0, 0);
        emit ActorRegistered(id, msg.sender, org);
    }
    function approveActor(bytes32 id) external onlyRole(REGISTRAR_ROLE) {
        require(actors[id].status == 1, "NOT_SELF_REGISTERED");
        actors[id].status = 2;
        actors[id].approvedAt = uint64(block.timestamp);
        emit ActorApproved(id);
    }
    function revokeActor(bytes32 id, uint64 effectiveFrom) external onlyRole(REGISTRAR_ROLE) {
        require(actors[id].signer != address(0), "UNKNOWN_ACTOR");
        require(effectiveFrom > 0 && effectiveFrom <= block.timestamp, "INVALID_REVOCATION_TIME");
        require(actors[id].revokedFrom == 0 || effectiveFrom < actors[id].revokedFrom, "CANNOT_RELAX_REVOCATION");
        actors[id].status = 3;
        actors[id].revokedFrom = effectiveFrom;
        emit ActorRevoked(id, effectiveFrom);
    }
    function hashEvent(EventData calldata e) public view returns(bytes32) {
        return _hashTypedDataV4(keccak256(abi.encode(EVENT_TYPEHASH, e.actorId, e.action, e.modelRef,
            keccak256(abi.encodePacked(e.parentEventIds)), keccak256(abi.encodePacked(e.inputSha256)),
            e.outputSha256, e.outputPixelSha256, e.outputPHash, e.paramsHash, e.privateRoot, e.claimedAt, e.nonce)));
    }
    function anchorEvent(EventData calldata e, bytes calldata signature) external returns(bytes32 id) {
        Actor memory a = actors[e.actorId];
        require(a.signer != address(0) && a.status != 3, "ACTOR_UNAVAILABLE");
        require(e.action >= 1 && e.action <= 13, "INVALID_ACTION");
        require(e.parentEventIds.length == e.inputSha256.length && e.parentEventIds.length <= 16, "PARENT_ALIGNMENT");
        require(e.outputSha256 != bytes32(0) && e.claimedAt <= block.timestamp + 300, "INVALID_EVENT");
        id = hashEvent(e);
        require(ECDSA.recover(id, signature) == a.signer, "SIGNER_MISMATCH");
        require(anchors[id].blockTime == 0, "DUPLICATE_EVENT");
        anchors[id] = Anchor(e.actorId, uint64(block.timestamp), uint64(block.number));
        if (firstClaim[e.outputSha256] == bytes32(0)) firstClaim[e.outputSha256] = id;
        emit EventAnchored(id, e.actorId, e.outputSha256);
    }
    function approveWitness(address who, bytes32 org) external onlyRole(WITNESS_ADMIN_ROLE) {
        require(who != address(0) && org != bytes32(0), "EMPTY_ID");
        require(witnesses[who].orgId == bytes32(0) || witnesses[who].orgId == org, "IMMUTABLE_ORG");
        witnesses[who] = WitnessInfo(org, true);
    }
    function revokeWitness(address who) external onlyRole(WITNESS_ADMIN_ROLE) { witnesses[who].approved = false; }
    function witness(bytes32 id, uint8 kind, bytes32 evidenceHash, bytes calldata signature) external {
        require(anchors[id].blockTime != 0, "UNKNOWN_EVENT");
        require(kind >= 1 && kind <= 3 && evidenceHash != bytes32(0), "INVALID_EVIDENCE");
        address who = ECDSA.recover(_hashTypedDataV4(keccak256(abi.encode(WITNESS_TYPEHASH, id, kind, evidenceHash))), signature);
        WitnessInfo memory w = witnesses[who];
        require(w.approved, "WITNESS_UNAPPROVED");
        require(w.orgId != actors[anchors[id].actorId].orgId, "NOT_INDEPENDENT");
        require(!witnessedBy[id][w.orgId], "DUPLICATE_ORG");
        witnessedBy[id][w.orgId] = true;
        records[id].push(WitnessRecord(who, w.orgId, kind, evidenceHash, uint64(block.timestamp)));
        emit Witnessed(id, who, w.orgId, kind, evidenceHash);
    }
    function anchorBatch(bytes32 root, uint32 count, string calldata uri) external onlyRole(REGISTRAR_ROLE) {
        require(root != bytes32(0) && count > 0 && bytes(uri).length <= 512, "INVALID_BATCH");
        require(batches[root].blockTime == 0, "DUPLICATE_BATCH");
        batches[root] = Batch(msg.sender, uint64(block.timestamp), count, uri);
        emit BatchAnchored(root, count, uri);
    }
    function verifyInclusion(bytes32 root, bytes32 leaf, bytes32[] calldata proof) external view returns(bool) {
        return batches[root].blockTime != 0 && MerkleProof.verifyCalldata(proof, root, leaf);
    }
    function setIssuer(address who) external onlyRole(REGISTRAR_ROLE) {
        require(who != address(0), "EMPTY_ID"); issuer = who; emit IssuerSet(who);
    }
    function getActor(bytes32 id) external view returns(Actor memory) { return actors[id]; }
    function getAnchor(bytes32 id) external view returns(Anchor memory) { return anchors[id]; }
    function witnessCount(bytes32 id) external view returns(uint256) { return records[id].length; }
    function getWitnesses(bytes32 id) external view returns(WitnessRecord[] memory) { return records[id]; }
}
